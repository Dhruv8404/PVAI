# Operations & Production Runbook

This document details common runbook tasks and operational APIs for administrators managing **PVAI**.

---

## 1. Operational Diagnostics Endpoint

Administrators can monitor live application performance by querying the operational diagnostics route:
* **Endpoint:** `GET /api/v1/ops/diagnostics`
* **Response Details:** Exposes active feature flags, cache hit/miss statistics, background worker heartbeat statuses, and database replication health.

```bash
curl -f https://api.pvai.com/api/v1/ops/diagnostics
```

---

## 2. Background Task Queue Management

The backend utilizes concurrent worker threads to offload CPU-intensive operations (report compilation, HTML formatting, and safety checks).

### Inspecting Backlogs
Query `/api/v1/ops/diagnostics` and check the `worker` section:
* `queue_backlog`: Number of pending tasks waiting for execution.
* `dead_letter_queue_size`: Count of failed tasks that exceeded max retries.
* `workers`: List of active threads with their latest heartbeat timestamps.

### Handling Task Failures (DLQ)
If a background job fails (e.g. LLM timeout), it enters a retry loop up to 3 times. If it still fails, it is cataloged in the **Dead-Letter Queue (DLQ)**.
* Check the last 10 failed tasks in the `dead_letter_queue_items` list.
* Log details record stack traces automatically under `storage/logs/error.log`.
