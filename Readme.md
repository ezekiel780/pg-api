# 📊 Transaction Ledger Reconciliation System

A backend service that reconciles transaction data between two systems (**SourceSystemA & SourceSystemB**) using large CSV files (1M+ rows supported) with asynchronous processing via Celery.

---

## 🚀 Features

- Upload two CSV files for reconciliation
- Detect:
  - Missing transactions in A or B
  - Amount mismatches
  - Status mismatches
- Async processing with Celery
- Redis-backed task queue
- REST API for status tracking
- Paginated job history
- Docker-ready architecture

---

## 🏗️ Tech Stack

- Python (Django / Django REST Framework)
- Celery (background processing)
- Redis (message broker)
- PostgreSQL / SQLite (depending on env)
- drf-spectacular (API docs)
- Docker (optional)

---

## 📂 Project Structure

pg-api/
│
├── reconciliation/
│   ├── views.py
│   ├── services.py
│   ├── tasks.py
│   ├── utils.py
│   ├── serializers.py
│   ├── models.py
│   └── urls.py
│
├── ledger/
├── media/ (ignored)
├── .env (ignored)
└── manage.py

---

## ⚙️ Setup Instructions

### 1. Clone repo
```bash
git clone https://github.com/ezekiel780/pg-api.git
cd pg-api
2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
4. Run migrations
python manage.py migrate
5. Start Redis (required for Celery)
redis-server
6. Start Celery worker
celery -A ledger worker -l info
7. Run server
python manage.py runserver
📡 API Endpoints
1. Upload CSVs for reconciliation
POST /api/v1/reconcile/

Form-data:

file_a → CSV file
file_b → CSV file
2. Check job status
GET /api/v1/status/<task_id>/
3. List all jobs (paginated)
GET /api/v1/reconcile/history/
📊 Example Response
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": {
    "missing_in_a": 1,
    "missing_in_b": 1,
    "amount_mismatch": 2,
    "status_mismatch": 1
  }
}
⚠️ Important Notes
.env is ignored (never push secrets)
media/ is ignored (contains uploaded files)
CSV files are uploaded via API only
Handles large files using streaming + hashing (O(n) memory)
🧪 Testing Flow
Upload CSVs → /reconcile/
Get task_id
Poll /status/<task_id>/
View results
Check history endpoint
🚀 Deployment (Render)
Connect GitHub repo
Add environment variables
Configure:
Redis service
Celery worker
Django web service
👨‍💻 Author

Built as part of PGTL Fullstack Software Assessment.


---

If you want next, I can help you:
👉 :contentReference[oaicite:0]{index=0}  
👉 or :contentReference[oaicite:1]{index=1}
