# Prometheus Monitoring & Metrics Integration

This document describes how to monitor **PVAI** system health, performance, and resource usage in production.

---

## 1. Metrics Endpoint

The system exposes structured metrics at `/metrics` conforming to the Prometheus text exposition format.
Metrics are split into:
* **HTTP Requests:** Counts and latencies grouped by method, path, and response status.
* **AI Operations:** Timings of embedding generation and LLM API calls.
* **System Stats:** Current system CPU, Memory, and Disk space usage.
* **Active Connections:** Active HTTP connections.

---

## 2. Metrics Definition List

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests handled. |
| `http_request_duration_seconds` | Histogram | `method`, `endpoint` | Request latencies in seconds. |
| `http_active_requests` | Gauge | - | Active HTTP requests being processed. |
| `ai_embedding_duration_seconds` | Histogram | - | Embedding generation duration. |
| `ai_llm_duration_seconds` | Histogram | `provider`, `model` | LLM generation duration. |
| `db_queries_total` | Counter | - | Total database queries executed. |
| `system_cpu_usage` | Gauge | - | System CPU usage percentage. |
| `system_mem_usage` | Gauge | - | System memory usage percentage. |
| `system_disk_usage` | Gauge | - | System root disk usage percentage. |

---

## 3. Prometheus Server Configuration

Add the following job scrape config block to your `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'pvai-backend'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['pvai-backend.onrender.com:443']
        labels:
          group: 'production'
```

---

## 4. Health Check Endpoint Splits

For load-balancer and container configurations, use the appropriate health route:

* **Liveness Probe (`/health/live`):** Quick ping confirming if the FastAPI process is running. (Fast & cheap, perfect for container restart policy).
* **Readiness Probe (`/health/ready`):** Confirms if the application is ready to handle queries. Checks PostgreSQL connection and local directory disk mount write capabilities. (Ideal for target group ingress routing).
* **Full Diagnostics Probe (`/health/full`):** Comprehensive system inspection (PostgreSQL, ChromaDB, SentenceTransformer preloaded model status, active LLM API connectivity, storage directories, background task queue). Expose to admin dashboard or alerts.
