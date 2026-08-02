# PVAI Deployment & Production Readiness Guide

This document describes the production deployment procedures for the **PVAI** (Pharmacovigilance AI & Document Generation Platform).

---

## 1. Production Architecture Overview

The system consists of the following production components:
* **Frontend Web Client:** React 19 app deployed on **Vercel**.
* **Backend API Service:** FastAPI service deployed on **Render** using a containerized Docker image.
* **Relational Database:** **Neon PostgreSQL** server.
* **Vector Database:** **ChromaDB** persisted on Render's local SSD volume.
* **Embeddings Model:** Local **SentenceTransformer (`BAAI/bge-small-en-v1.5`)** preloaded on startup.
* **Media & Upload Vault:** **Cloudinary** storage.
* **LLM APIs:** Switchable provider (Gemini or OpenAI in production, OmniRoute/Ollama in local).

---

## 2. Environment Variables Specification

Ensure all variables are configured in the Render/Vercel dashboards as environment variables.

| Variable Name | Required | Default Value | Deployment Scope | Description |
|---|---|---|---|---|
| `ENV` | Yes | `production` | Backend | Set to `production` to activate strict checks. |
| `DATABASE_URL` | Yes | - | Backend | Neon PostgreSQL async connection string (`postgresql+asyncpg://...`). |
| `SECRET_KEY` | Yes | - | Backend | High-entropy key for general encryption. |
| `JWT_SECRET` | Yes | - | Backend | Dedicated high-entropy key for JWT signature encoding. |
| `JWT_ALGORITHM` | Yes | `HS256` | Backend | Signature verification algorithm (defaults to `HS256`). |
| `FRONTEND_URL` | Yes | - | Backend | URL of the frontend deployed on Vercel. |
| `CORS_ORIGINS` | Yes | - | Backend | Comma-separated list of accepted frontend URLs. |
| `STORAGE_TYPE` | No | `cloudinary` | Backend | Storage strategy (`local` or `cloudinary`). |
| `CLOUDINARY_CLOUD_NAME` | No | - | Backend | Cloudinary cloud identifier (if strategy is Cloudinary). |
| `CLOUDINARY_API_KEY` | No | - | Backend | Cloudinary API access key. |
| `CLOUDINARY_API_SECRET` | No | - | Backend | Cloudinary API write signature. |
| `CHROMA_DB_PATH` | No | `/var/data/chromadb` | Backend | Path on the mounted Render persistent disk. |
| `EMBEDDING_MODEL` | No | `BAAI/bge-small-en-v1.5` | Backend | Name of local embeddings model to fetch. |
| `LLM_PROVIDER` | No | `gemini` | Backend | Selected LLM (`gemini`, `openai`, `omniroute`, `ollama`). |
| `GEMINI_API_KEY` | No | - | Backend | Google AI API Key (required if LLM_PROVIDER is gemini). |
| `OPENAI_API_KEY` | No | - | Backend | OpenAI API Key (required if LLM_PROVIDER is openai). |
| `VITE_API_URL` | Yes | - | Frontend | API Base endpoint for HTTP calls (`https://<app>.onrender.com/api/v1`). |

---

## 3. Database Deployment (Neon PostgreSQL)

1. Sign up/Log in to the **[Neon Console](https://neon.tech)**.
2. Create a new project and database named `docgen_db`.
3. Retrieve the connection details. **Make sure to select the `Pooled Connection` and select the `asyncpg` dialect format** (using prefix `postgresql+asyncpg://...`).
4. Paste this connection URL into the `DATABASE_URL` environment variable for your Render service.
5. Startup lifespan will run SQL schema creations automatically.

---

## 4. Backend Deployment (Render)

### Automatic Deployment (Recommended)
This repository contains a `render.yaml` specification that allows one-click infrastructure deployments.
1. Go to the **Blueprints** section in the Render dashboard.
2. Connect your GitHub repository.
3. Render will parse `render.yaml` and prompt you to input the sync variables (PostgreSQL, Cloudinary, Gemini/OpenAI API Keys).
4. Click **Deploy**.

### Manual Deployment
If deploying manually:
1. Create a new **Web Service** on Render.
2. Select **Docker** as the environment (Render will build utilizing `backend/Dockerfile`).
3. Set the Docker Context directory to `backend`.
4. Add a **Persistent Disk** under **Advanced Settings**:
   * **Name:** `pvai-chroma-data`
   * **Mount Path:** `/var/data`
   * **Size:** `10 GB` (or larger depending on dataset sizes)
5. Fill in the environment variables specified in Section 2. Set `CHROMA_DB_PATH` to `/var/data/chromadb`.
6. Start command will execute container entrypoint automatically.

---

## 5. Frontend Deployment (Vercel)

1. Connect your repository to **Vercel**.
2. Create a new Vercel project selecting the root workspace directory.
3. Configure the build settings:
   * **Framework Preset:** Vite
   * **Root Directory:** `./`
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
4. Add the `VITE_API_URL` environment variable, pointing to your Render service address (e.g. `https://pvai-backend.onrender.com/api/v1`).
5. Click **Deploy**.

---

## 6. Database Migrations (Production Execution)

Instead of dynamic table creation, always execute Alembic migrations on deployment:
```bash
# Apply pending schemas to Neon DB
alembic upgrade head
```

---

## 7. Diagnostics, Monitoring & Troubleshooting

### Split Health Endpoints
Choose the appropriate route depending on your load-balancer/container requirements:
* **Liveness (`/health/live`):** Basic FastAPI status check.
* **Readiness (`/health/ready`):** Confirms PostgreSQL database connectivity and storage folder health.
* **Full Diagnostics (`/health/full` or `/health`):** Exhaustive checks including ChromaDB collections, local SentenceTransformer preloaded status, LLM provider connections, and worker task statuses.

### Prometheus Metrics
Expose application metrics to your Prometheus instance by scraping the `/metrics` endpoint:
```bash
curl -f https://<your-backend-url>.onrender.com/metrics
```

### Common Issues
* **FastAPI Startup Times out on Render:** The local SentenceTransformer model takes ~30-60 seconds to download and cache on its first start. If Render hits a health check timeout:
  * Increase the Render service **Web Service Health Check Timeout** parameter to 120 seconds.
* **CORS Blocked Errors:** Verify that the frontend address is added precisely (without trailing slashes) in `CORS_ORIGINS` and `FRONTEND_URL` on the backend service.
* **503 Service Unavailable:** If this is returned, check that Neon database credentials are correct or verify ChromaDB Persistent Disk is mounted correctly at `/var/data`.

