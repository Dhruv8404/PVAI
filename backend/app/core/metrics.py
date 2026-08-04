import time
import shutil
import logging
import threading
from typing import Tuple

logger = logging.getLogger("app.startup")

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    from prometheus_client.registry import DuplicateTimeseries
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False


class DummyMetric:
    def __init__(self, *args, **kwargs): pass
    def labels(self, *args, **kwargs): return self
    def inc(self, *args, **kwargs): pass
    def dec(self, *args, **kwargs): pass
    def observe(self, *args, **kwargs): pass
    def set(self, *args, **kwargs): pass


def _create_metric(cls, name, documentation, *args, **kwargs):
    if not HAS_PROMETHEUS:
        return DummyMetric()
    try:
        return cls(name, documentation, *args, **kwargs)
    except Exception as e:
        if "DuplicateTimeseries" in type(e).__name__ or "Duplicated" in str(e):
            if hasattr(REGISTRY, "_names_to_collectors") and name in REGISTRY._names_to_collectors:
                return REGISTRY._names_to_collectors[name]
        raise e


# Define all metrics if prometheus_client library is available
if HAS_PROMETHEUS:
    HTTP_REQUESTS_TOTAL = _create_metric(
        Counter,
        "http_requests_total",
        "Total HTTP requests handled by the server",
        ["method", "endpoint", "status"]
    )
    
    HTTP_REQUEST_DURATION_SECONDS = _create_metric(
        Histogram,
        "http_request_duration_seconds",
        "HTTP request latencies in seconds",
        ["method", "endpoint"]
    )
    
    ACTIVE_REQUESTS = _create_metric(
        Gauge,
        "http_active_requests",
        "Current number of active requests being processed"
    )
    
    AI_EMBEDDING_DURATION_SECONDS = _create_metric(
        Histogram,
        "ai_embedding_duration_seconds",
        "Duration of vector embedding generations in seconds"
    )
    
    AI_LLM_DURATION_SECONDS = _create_metric(
        Histogram,
        "ai_llm_duration_seconds",
        "Duration of LLM provider generations in seconds",
        ["provider", "model"]
    )
    
    DB_QUERIES_TOTAL = _create_metric(
        Counter,
        "db_queries_total",
        "Total database queries executed by application"
    )
    
    DB_QUERY_DURATION_SECONDS = _create_metric(
        Histogram,
        "db_query_duration_seconds",
        "Database query execution duration in seconds"
    )
    
    SYSTEM_CPU_USAGE = _create_metric(
        Gauge,
        "system_cpu_usage",
        "System CPU usage percentage"
    )
    
    SYSTEM_MEM_USAGE = _create_metric(
        Gauge,
        "system_mem_usage",
        "System memory usage percentage"
    )
    
    SYSTEM_DISK_USAGE = _create_metric(
        Gauge,
        "system_disk_usage",
        "System root disk usage percentage"
    )

    SYSTEM_THREAD_COUNT = _create_metric(
        Gauge,
        "system_thread_count",
        "Total active application threads"
    )

    SYSTEM_FILE_DESCRIPTORS = _create_metric(
        Gauge,
        "system_file_descriptors",
        "Total open file descriptors or handles"
    )

    EVENT_LOOP_LATENCY = _create_metric(
        Gauge,
        "system_event_loop_latency_seconds",
        "FastAPI asyncio event loop latency in seconds"
    )

    ACTIVE_USERS_GAUGE = _create_metric(
        Gauge,
        "active_users_count",
        "Total active unique users detected by system"
    )

    HTTP_RESPONSE_SIZE_BYTES = _create_metric(
        Histogram,
        "http_response_size_bytes",
        "HTTP response size in bytes"
    )

    QUEUE_BACKLOG = _create_metric(
        Gauge,
        "task_queue_backlog",
        "Total pending tasks in queue"
    )
    
    WORKER_ACTIVE_GAUGE = _create_metric(
        Gauge,
        "task_worker_active_count",
        "Total active worker threads"
    )
    
    TASKS_PROCESSED = _create_metric(
        Counter,
        "task_processed_total",
        "Total tasks processed",
        ["status"]
    )

    CACHE_HITS = _create_metric(
        Counter,
        "cache_hits_total",
        "Total cache hits",
        ["cache_type"]
    )

    CACHE_MISSES = _create_metric(
        Counter,
        "cache_misses_total",
        "Total cache misses",
        ["cache_type"]
    )
else:
    HTTP_REQUESTS_TOTAL = DummyMetric()
    HTTP_REQUEST_DURATION_SECONDS = DummyMetric()
    ACTIVE_REQUESTS = DummyMetric()
    AI_EMBEDDING_DURATION_SECONDS = DummyMetric()
    AI_LLM_DURATION_SECONDS = DummyMetric()
    DB_QUERIES_TOTAL = DummyMetric()
    DB_QUERY_DURATION_SECONDS = DummyMetric()
    SYSTEM_CPU_USAGE = DummyMetric()
    SYSTEM_MEM_USAGE = DummyMetric()
    SYSTEM_DISK_USAGE = DummyMetric()
    SYSTEM_THREAD_COUNT = DummyMetric()
    SYSTEM_FILE_DESCRIPTORS = DummyMetric()
    EVENT_LOOP_LATENCY = DummyMetric()
    ACTIVE_USERS_GAUGE = DummyMetric()
    HTTP_RESPONSE_SIZE_BYTES = DummyMetric()
    QUEUE_BACKLOG = DummyMetric()
    WORKER_ACTIVE_GAUGE = DummyMetric()
    TASKS_PROCESSED = DummyMetric()
    CACHE_HITS = DummyMetric()
    CACHE_MISSES = DummyMetric()
    
    Gauge = DummyMetric
    Counter = DummyMetric
    Histogram = DummyMetric


# Set of active unique users tracked during runtime
_active_user_ids = set()


def record_active_user(user_id: str):
    """Tracks unique active user accounts in memory for metrics monitoring."""
    if user_id:
        _active_user_ids.add(user_id)
        if HAS_PROMETHEUS:
            ACTIVE_USERS_GAUGE.set(len(_active_user_ids))


async def get_system_metrics() -> Tuple[float, float, float]:
    """Retrieves system resource statistics (CPU, Memory, Disk, Thread and FD counts)."""
    # 1. Disk usage
    disk_percent = 0.0
    try:
        total, used, free = shutil.disk_usage("/")
        disk_percent = (used / total) * 100
    except Exception:
        pass
        
    # 2. CPU & Memory usage (if psutil library is present)
    cpu_percent = 0.0
    mem_percent = 0.0
    num_fds = 0
    try:
        import psutil
        cpu_percent = psutil.cpu_percent()
        mem_percent = psutil.virtual_memory().percent
        
        proc = psutil.Process()
        # On Windows, num_fds doesn't exist, we must use num_handles
        if hasattr(proc, "num_handles"):
            num_fds = proc.num_handles()
        else:
            num_fds = proc.num_fds()
    except ImportError:
        pass
    except Exception:
        pass

    # 3. Thread count
    thread_count = threading.active_count()

    # 4. Async Event Loop Latency calculation
    event_loop_lag = 0.0
    try:
        import asyncio
        start_time = time.time()
        # Measure drift by forcing scheduler to run a no-op task
        await asyncio.sleep(0.0)
        event_loop_lag = time.time() - start_time
    except Exception:
        pass
        
    # Update Gauges
    if HAS_PROMETHEUS:
        SYSTEM_CPU_USAGE.set(cpu_percent)
        SYSTEM_MEM_USAGE.set(mem_percent)
        SYSTEM_DISK_USAGE.set(disk_percent)
        SYSTEM_THREAD_COUNT.set(thread_count)
        SYSTEM_FILE_DESCRIPTORS.set(num_fds)
        EVENT_LOOP_LATENCY.set(event_loop_lag)
        ACTIVE_USERS_GAUGE.set(len(_active_user_ids))
        
    return cpu_percent, mem_percent, disk_percent
