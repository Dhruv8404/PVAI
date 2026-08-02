# Enterprise Scaling & High Availability Blueprint

This document details horizontal and vertical scaling blueprints for **PVAI** in enterprise environments.

---

## 1. Stateless Architecture

The backend application is completely stateless. Session state, authentication (JWT), and transactions reside outside the FastAPI containers (in Neon PostgreSQL, Cloudinary, and Redis).
This enables instant horizontal scaling:

```mermaid
graph TD
  LoadBalancer[Application Load Balancer] --> FastAPI_1[FastAPI Node 1]
  LoadBalancer --> FastAPI_2[FastAPI Node 2]
  LoadBalancer --> FastAPI_3[FastAPI Node 3]
  
  FastAPI_1 --> PostgreSQL[(Neon Database)]
  FastAPI_2 --> PostgreSQL
  FastAPI_3 --> PostgreSQL
  
  FastAPI_1 --> Redis[(Redis Cache & Rate-limit)]
  FastAPI_2 --> Redis
  FastAPI_3 --> Redis
```

---

## 2. Queue Scaling (Celery Integration Path)

Currently, the task queue runs as an in-memory thread pool inside FastAPI container memory.
To support heavy scale:
1. Swap `app/core/task_queue.py` to route tasks to a distributed worker system (e.g. Celery + RabbitMQ/Redis).
2. Spin up separate worker containers executing identical business functions, leaving the API containers 100% free to handle HTTP traffic.

---

## 3. Database Scaling (Neon Connection Pooling)

FastAPI nodes utilize connection pooling with a pool size of 20 and overflow limit of 10.
* For multi-node deployments, make sure database connection limits are configured to support `Nodes * Pool Size`.
* Connect using **Neon Transaction Pooling** connection endpoints (`-pooler` suffix in hostname) to share connections efficiently.
