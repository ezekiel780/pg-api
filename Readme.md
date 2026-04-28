# 📊 Transaction Ledger Reconciliation System

A full-stack financial reconciliation platform that detects discrepancies between two source system CSV transaction files. Built with Django, Celery, Redis, React, and TypeScript.

---

## 🔗 Live Links

| Service | URL |
|---|---|
| Frontend | https://ledger-csv-kappa.vercel.app |
| Backend API | https://pg-api-7mfb.onrender.com |
| Swagger UI | https://pg-api-7mfb.onrender.com/api/docs |
| API Schema | https://pg-api-7mfb.onrender.com/api/schema |

---

## 📁 Repository Links

| Repo | Link |
|---|---|
| Backend (Django) | https://github.com/ezekiel780/pg-api |
| Frontend (React) | https://github.com/ezekiel780/pg-frontend |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        VERCEL                            │
│   React + TypeScript + Vite (Static Site)               │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API calls (HTTPS)
┌──────────────────────▼──────────────────────────────────┐
│                       RENDER                             │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐    │
│  │   Django API    │───▶│     Celery Worker        │    │
│  │  DRF + Gunicorn │    │  Async CSV processing    │    │
│  └────────┬────────┘    └──────────┬───────────────┘    │
│           │                        │                     │
│           │             ┌──────────▼───────────────┐    │
│           │             │   Reconciliation Engine   │    │
│           │             │  stream_csv + services    │    │
│           │             └───────────────────────────┘    │
└───────────┼─────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────┐
│                      CLOUD DATA                          │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Upstash Redis│  │Render Postgres│  │ Media Storage │  │
│  │   (Broker)   │  │ Jobs+Results  │  │  CSV uploads  │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Features

- Upload two CSV transaction files (Source System A and Source System B)
- Detects four types of discrepancies:
  - Transactions missing in A
  - Transactions missing in B
  - Amount mismatches (normalised with `Decimal` — handles `100.00` vs `100.0`)
  - Status mismatches (case-insensitive — handles `SUCCESS` vs `success`)
- Async processing via Celery — handles 1M+ row files without timeouts
- Auto-polling every 3 seconds until job completes
- Job history table with status badges
- Cancel running jobs
- Paginated API responses
- Swagger UI documentation

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| Python 3.11 | Language |
| Django 4.x | Web framework |
| Django REST Framework | API layer |
| Celery | Async task queue |
| Gunicorn | WSGI server |
| PostgreSQL | Primary database |
| Redis (Upstash) | Celery broker + result backend |
| drf-spectacular | OpenAPI / Swagger docs |

### Frontend
| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool |
| Axios | HTTP client |

### Infrastructure
| Service | Purpose |
|---|---|
| Render | Backend hosting |
| Vercel | Frontend hosting |
| Upstash | Managed Redis (TLS) |
| Render Postgres | Managed PostgreSQL |

---

## 📂 Project Structure

### Backend
```
pg-api/
├── core/                        # Django project package
│   ├── settings.py              # All configuration
│   ├── urls.py                  # Root URL routing
│   ├── celery.py                # Celery app init
│   ├── wsgi.py
│   └── asgi.py
├── reconciliation/              # Main Django app
│   ├── models.py                # ReconciliationJob model
│   ├── views.py                 # API views
│   ├── serializers.py           # Request validation
│   ├── services.py              # Reconciliation logic (O(N) memory)
│   ├── tasks.py                 # Celery tasks
│   ├── utils.py                 # CSV streaming helper
│   ├── urls.py                  # App URL patterns
│   └── admin.py                 # Django admin config
├── Scripts/
│   ├── start.sh                 # Render start script
│   └── dev_start.sh             # Local dev start script
├── nginx/                       # Nginx config (local Docker)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

### Frontend
```
reconciliation-ui/
├── src/
│   ├── api/
│   │   └── reconciliation.ts    # All API functions
│   ├── config/
│   │   └── api.ts               # Base URL + endpoints
│   ├── pages/
│   │   └── Dashboard.tsx        # Main page
│   ├── types/
│   │   └── index.ts             # TypeScript interfaces
│   ├── App.tsx                  # Root shell
│   ├── App.css                  # All styles
│   └── main.tsx                 # Entry point
├── .env                         # Local env vars
├── .env.production              # Production env vars
├── vite.config.ts
├── package.json
└── index.html
```

---

## 📋 CSV File Format

Both uploaded files must be CSV with these required columns:

```csv
transaction_id,amount,status,timestamp,currency
TXN001,100.00,SUCCESS,2024-01-01T10:00:00,USD
TXN002,250.50,FAILED,2024-01-01T10:05:00,USD
TXN003,75.00,SUCCESS,2024-01-01T10:10:00,USD
```

| Column | Required | Notes |
|---|---|---|
| `transaction_id` | ✅ | Unique identifier per transaction |
| `amount` | ✅ | Decimal — `100.00` and `100.0` treated as equal |
| `status` | ✅ | Case-insensitive — `SUCCESS` and `success` treated as equal |
| `timestamp` | ❌ | Optional — preserved but not compared |
| `currency` | ❌ | Optional — preserved but not compared |

---

## 🚀 Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- Git

### Step 1 — Clone the repos

```bash
# Backend
git clone https://github.com/ezekiel780/pg-api.git
cd pg-api

# Frontend (separate terminal)
git clone https://github.com/ezekiel780/pg-frontend.git
cd pg-frontend/reconciliation-ui
```

### Step 2 — Backend environment

Create `.env` in the `pg-api/` root:

```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://postgres:postgres@db:5432/ledger_recon
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
DB_NAME=ledger_recon
DB_USER=postgres
DB_PASSWORD=postgres
```

### Step 3 — Start backend with Docker

```bash
cd pg-api
docker-compose up --build
```

This starts:
- Django API on `http://localhost:8000`
- Celery worker
- Celery beat scheduler
- PostgreSQL on port 5432
- Redis on port 6379

### Step 4 — Frontend environment

Create `.env` in `reconciliation-ui/`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_API_TIMEOUT_MS=30000
```

### Step 5 — Start frontend

```bash
cd reconciliation-ui
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### Step 6 — Verify everything is working

```bash
# Check Django is up
curl http://localhost:8000/health/

# Check Swagger UI
open http://localhost:8000/api/docs/

# Check frontend
open http://localhost:3000
```

---

## 🔌 API Reference

Base URL: `https://pg-api-7mfb.onrender.com/api/v1`

### POST `/reconcile/`
Submit two CSV files for reconciliation.

**Request:** `multipart/form-data`
| Field | Type | Required |
|---|---|---|
| `file_a` | CSV file | ✅ |
| `file_b` | CSV file | ✅ |

**Response 202:**
```json
{
  "task_id": "4f245f9c-914d-480c-8257-ec23d311d442",
  "status": "PENDING"
}
```

---

### GET `/reconcile/{task_id}/`
Poll the status and result of a job.

**Response 200:**
```json
{
  "task_id": "4f245f9c-914d-480c-8257-ec23d311d442",
  "status": "SUCCESS",
  "created_at": "2026-04-27T01:24:31Z",
  "result": {
    "total_a": 1000000,
    "total_b": 999998,
    "missing_in_a": 1,
    "missing_in_b": 3,
    "amount_mismatch": 12,
    "status_mismatch": 5,
    "details_capped": false
  }
}
```

**Job statuses:**
| Status | Meaning |
|---|---|
| `PENDING` | Queued, not yet started |
| `PROCESSING` | Worker is reading CSV files |
| `SUCCESS` | Reconciliation complete |
| `FAILED` | Error during processing |
| `CANCELLED` | Cancelled by user |

---

### GET `/reconcile/history/`
Paginated list of all reconciliation jobs.

**Query params:** `?page=1&page_size=50`

**Response 200:**
```json
{
  "count": 42,
  "next": "/api/v1/reconcile/history/?page=2",
  "previous": null,
  "results": [
    {
      "task_id": "4f245f9c-...",
      "status": "SUCCESS",
      "file_a": "source_system_a.csv",
      "file_b": "source_system_b.csv",
      "created_at": "2026-04-27T01:24:31Z"
    }
  ]
}
```

---

### POST `/reconcile/{task_id}/cancel/`
Cancel a pending or processing job.

**Response 200:**
```json
{
  "task_id": "4f245f9c-...",
  "status": "CANCELLED"
}
```

---

### GET `/health/`
Health check endpoint for load balancers.

**Response 200:**
```json
{ "status": "ok" }
```

---

## 🗄️ Database Schema

```
ReconciliationJob
─────────────────────────────────────────────
id            BigAutoField    PK
task_id       CharField(255)  unique, indexed
file_a_name   CharField(255)
file_b_name   CharField(255)
file_a_path   CharField(500)  null
file_b_path   CharField(500)  null
status        CharField(20)   indexed
              PENDING | PROCESSING | SUCCESS
              FAILED  | CANCELLED
result        JSONField       null
              {
                summary: { total_a, total_b,
                  missing_in_a, missing_in_b,
                  amount_mismatch, status_mismatch,
                  details_capped },
                details: { missing_in_a[], missing_in_b[],
                  amount_mismatch[], status_mismatch[] }
              }
error         TextField       null
created_at    DateTimeField   auto, indexed
updated_at    DateTimeField   auto
```

---

## ⚙️ Render Deployment

### Environment Variables (all 3 services)

```env
DJANGO_SETTINGS_MODULE  = core.settings
DEBUG                   = False
DJANGO_SECRET_KEY       = <generate with: python -c "import secrets; print(secrets.token_urlsafe(50))">
DATABASE_URL            = <Render Postgres internal URL>
DB_SSL_MODE             = require
REDIS_URL               = rediss://default:<token>@magnetic-spider-107053.upstash.io:6379
CELERY_BROKER_URL       = rediss://default:<token>@magnetic-spider-107053.upstash.io:6379/0?ssl_cert_reqs=CERT_NONE
CELERY_RESULT_BACKEND   = rediss://default:<token>@magnetic-spider-107053.upstash.io:6379/0?ssl_cert_reqs=CERT_NONE
ALLOWED_HOSTS           = pg-api-7mfb.onrender.com
CORS_ALLOWED_ORIGINS    = https://ledger-csv-kappa.vercel.app,http://localhost:3000
RENDER_EXTERNAL_HOSTNAME= pg-api-7mfb.onrender.com
```

### Start Command (Web Service)

```bash
sh Scripts/start.sh
```

---

## ⚡ Performance Design

| Concern | Solution |
|---|---|
| Large file memory | `stream_csv()` yields one row at a time — O(1) memory |
| Comparison memory | Load file A into hashmap, stream file B — O(N) peak not O(2N) |
| Amount comparison | `Decimal` normalisation — `100.00` == `100.0` |
| Status comparison | `.upper()` normalisation — `SUCCESS` == `success` |
| Large cell fields | `csv.field_size_limit(1MB)` — prevents `_csv.Error` crash |
| Result storage | Detail lists capped at 10,000 IDs — summary counts always accurate |
| Worker memory | `CELERY_WORKER_MAX_MEMORY_PER_CHILD=1GB` — auto-restarts on leak |
| Task loss on crash | `CELERY_TASK_ACKS_LATE=True` — task re-queued if worker dies |
| Queue starvation | `CELERY_WORKER_PREFETCH_MULTIPLIER=1` — one task at a time |

---

## 🧪 Running Tests

```bash
cd pg-api
python manage.py test reconciliation
```

---

## 📝 Notes

- Detail lists (missing IDs, mismatched IDs) are capped at 10,000 entries per category. The `details_capped` flag in the response indicates when this limit is hit. Summary counts are always fully accurate regardless of the cap.
- Uploaded CSV files are automatically deleted from disk after a job completes.
- A nightly cleanup task runs at 3 AM (Africa/Lagos) to remove any orphaned files older than 24 hours.
- Free tier Render instances spin down after inactivity — the first request after a cold start may take 30–60 seconds.

---

## 👤 Author

**Ezekiel Balogun**
GitHub: [@ezekiel780](https://github.com/ezekiel780)
