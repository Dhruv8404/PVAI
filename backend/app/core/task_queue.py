import uuid
import queue
import logging
import time
import threading
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, UTC
from app.core.metrics import HAS_PROMETHEUS, Gauge, Counter

logger = logging.getLogger("app.startup")

# Global registries for distributed-like task tracking
task_registry: Dict[str, Dict[str, Any]] = {}
dead_letter_queue: List[Dict[str, Any]] = []

# Worker heartbeat registry: worker_name -> last_heartbeat_timestamp
worker_heartbeats: Dict[str, float] = {}

# Thread-safe PriorityQueue: items are (priority_int, timestamp, task_id, func, args, kwargs)
# High = 1, Default = 2, Low = 3
_task_queue = queue.PriorityQueue()

# Queue metrics if Prometheus is active
if HAS_PROMETHEUS:
    QUEUE_BACKLOG = Gauge("task_queue_backlog", "Total pending tasks in queue")
    WORKER_ACTIVE_GAUGE = Gauge("task_worker_active_count", "Total active worker threads")
    TASKS_PROCESSED = Counter("task_processed_total", "Total tasks processed", ["status"])
else:
    class DummyMetric:
        def set(self, val): pass
        def inc(self): pass
        def labels(self, *args, **kwargs): return self
    QUEUE_BACKLOG = DummyMetric()
    WORKER_ACTIVE_GAUGE = DummyMetric()
    TASKS_PROCESSED = DummyMetric()


class BackgroundWorker(threading.Thread):
    """Worker thread pulling tasks from the PriorityQueue."""
    
    def __init__(self, name: str, task_queue: queue.PriorityQueue):
        super().__init__()
        self.name = name
        self.queue = task_queue
        self.daemon = True
        self._stop_event = threading.Event()

    def run(self):
        logger.info(f"[WORKER-{self.name}] Thread started.")
        WORKER_ACTIVE_GAUGE.inc()
        
        while not self._stop_event.is_set():
            # Heartbeat check-in
            worker_heartbeats[self.name] = time.time()
            
            try:
                # Wait for task
                item = self.queue.get(timeout=2.0)
            except queue.Empty:
                continue
                
            priority, timestamp, task_id, func, args, kwargs = item
            QUEUE_BACKLOG.set(self.queue.qsize())
            
            # Task status check
            task_info = task_registry.get(task_id)
            if not task_info:
                self.queue.task_done()
                continue
                
            logger.info(f"[WORKER-{self.name}] Executing task '{func.__name__}' (ID: {task_id}) [Priority: {priority}]")
            task_info.update({
                "status": "RUNNING",
                "worker_name": self.name,
                "updated_at": datetime.now(UTC)
            })
            
            try:
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    loop = asyncio.new_event_loop()
                    try:
                        result = loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    result = func(*args, **kwargs)
                    
                task_info.update({
                    "status": "COMPLETED",
                    "result": result,
                    "updated_at": datetime.now(UTC)
                })
                TASKS_PROCESSED.labels(status="success").inc()
                logger.info(f"[WORKER-{self.name}] Task (ID: {task_id}) completed.")
            except Exception as e:
                # Handle retries
                retries = task_info.get("retries", 0)
                max_retries = task_info.get("max_retries", 3)
                
                if retries < max_retries:
                    new_retries = retries + 1
                    task_info.update({
                        "status": "RETRYING",
                        "retries": new_retries,
                        "error": str(e),
                        "updated_at": datetime.now(UTC)
                    })
                    logger.warning(
                        f"[WORKER-{self.name}] Task {task_id} failed ({e}). "
                        f"Retry {new_retries}/{max_retries} scheduled."
                    )
                    # Re-enqueue task (increase timestamp to place at back, preserve priority)
                    self.queue.put((priority, time.time(), task_id, func, args, kwargs))
                    QUEUE_BACKLOG.set(self.queue.qsize())
                else:
                    # Move to Dead-Letter Queue (DLQ)
                    task_info.update({
                        "status": "FAILED",
                        "error": str(e),
                        "updated_at": datetime.now(UTC)
                    })
                    dlq_item = {
                        "task_id": task_id,
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "error": str(e),
                        "failed_at": datetime.now(UTC).isoformat() + "Z"
                    }
                    dead_letter_queue.append(dlq_item)
                    TASKS_PROCESSED.labels(status="failure").inc()
                    logger.error(
                        f"[WORKER-{self.name}] Task {task_id} exceeded max retries. "
                        f"Moved to Dead-Letter Queue."
                    )
            finally:
                self.queue.task_done()
                
        WORKER_ACTIVE_GAUGE.dec()
        logger.info(f"[WORKER-{self.name}] Thread stopped.")

    def stop(self):
        self._stop_event.set()


# Active worker pool registry
_workers: List[BackgroundWorker] = []
_worker_lock = threading.Lock()
MAX_CONCURRENT_WORKERS = 3


def start_worker():
    """Starts the pool of concurrent background task workers."""
    global _workers
    with _worker_lock:
        if not _workers:
            for i in range(1, MAX_CONCURRENT_WORKERS + 1):
                w = BackgroundWorker(name=f"thread-{i}", task_queue=_task_queue)
                w.start()
                _workers.append(w)
            logger.info(f"[BACKGROUND TASK WORKER] Started pool of {MAX_CONCURRENT_WORKERS} workers.")


def stop_worker():
    """Gracefully stops all running background task workers."""
    global _workers
    with _worker_lock:
        for w in _workers:
            w.stop()
        _workers = []
        logger.info("[BACKGROUND TASK WORKER] Stopped all worker threads.")


def enqueue_task(func: Callable, *args, priority: int = 2, max_retries: int = 3, **kwargs) -> str:
    """Enqueues a background task specifying queue priority (1=High, 2=Default, 3=Low)."""
    start_worker()
    
    task_id = str(uuid.uuid4())
    task_registry[task_id] = {
        "status": "PENDING",
        "result": None,
        "error": None,
        "retries": 0,
        "max_retries": max_retries,
        "priority": priority,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    
    # Put onto PriorityQueue: tuple sorted order handles priority_int first
    # time.time() provides secondary sort (FIFO for same priority)
    _task_queue.put((priority, time.time(), task_id, func, args, kwargs))
    QUEUE_BACKLOG.set(_task_queue.qsize())
    
    logger.info(f"[BACKGROUND TASK] Enqueued '{func.__name__}' [Task ID: {task_id}, Priority: {priority}]")
    return task_id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves current execution info for a specific task."""
    return task_registry.get(task_id)


def get_worker_status() -> Dict[str, Any]:
    """Returns detailed statistics about workers, queues, heartbeats, and DLQs."""
    now = time.time()
    active_workers = []
    
    # Check worker health by inspecting heartbeats (active if checked in within last 5s)
    for name, last_check in list(worker_heartbeats.items()):
        is_healthy = (now - last_check) < 10.0
        active_workers.append({
            "name": name,
            "status": "healthy" if is_healthy else "offline",
            "last_heartbeat": datetime.fromtimestamp(last_check, UTC).isoformat() + "Z"
        })
        
    return {
        "active_threads_count": len(_workers),
        "workers": active_workers,
        "queue_backlog": _task_queue.qsize(),
        "total_tasks_tracked": len(task_registry),
        "dead_letter_queue_size": len(dead_letter_queue),
        "dead_letter_queue_items": dead_letter_queue[-10:]  # returns last 10 failed items
    }
