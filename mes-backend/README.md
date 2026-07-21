# MES Backend — Django REST API

**Medical Equipment Sharing Platform** — A rental marketplace for medical equipment in Tanzania, connecting healthcare facilities (buyers) with equipment vendors (merchants).

---

## Project Structure

```
mes-backend/
├── config/                  # Django project configuration (settings, URLs, WSGI, Celery)
├── apps/                    # Django applications (modular by domain)
│   ├── core/                # Shared framework: responses, pagination, permissions, exceptions
│   ├── accounts/            # User registration, login, OTP verification, profile management
│   ├── addresses/           # Delivery and billing address management (buyer-owned)
│   ├── equipment/           # Product catalog: listings, images, availability blocks
│   ├── cart/                # Shopping cart: add/remove items, validate before checkout
│   ├── bookings/            # Order lifecycle: checkout, order groups, sub-orders, status machine
│   ├── payments/            # Snippe payment gateway: initiate, webhook, status tracking
│   ├── contracts/           # PDF rental agreements: generate, sign, retrieve
│   └── notifications/       # In-app notifications, SMS (SendAfrica), push (FCM)
├── manage.py                # Django management entry point
├── test_e2e.py              # End-to-end integration test (21 steps, 52 assertions)
├── Dockerfile               # Production container (Python 3.12-slim, Gunicorn)
├── docker-compose.yml       # Full stack: api, db (Postgres), redis, celery, nginx
├── nginx.conf               # Reverse proxy configuration
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── .dockerignore            # Docker build exclusions
```

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/troubleman96/MES-API.git
cd MES-API/mes-backend
cp .env.example .env
# Edit .env with your actual API keys
```

### 2. Run with Docker (recommended)

```bash
docker compose up -d
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser  # optional
docker compose exec api python manage.py seed_data        # seed test data
```

API available at `http://localhost:8000` (via Nginx) or `http://localhost:8000` (direct).

### 3. Run locally (development)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ensure PostgreSQL and Redis are running locally
export POSTGRES_HOST=localhost POSTGRES_PORT=5433
export REDIS_URL=redis://localhost:6380/1

python manage.py migrate
python manage.py runserver
```

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Django | 5.1 |
| API | Django REST Framework | 3.15 |
| Auth | JWT (simplejwt) | 5.3 |
| Database | PostgreSQL | 16 |
| Cache / Queue | Redis | 7 |
| Task Queue | Celery | 5.4 |
| PDF Generation | ReportLab | 4.2 |
| SMS Gateway | SendAfrica | REST API |
| Payment Gateway | Snippe | REST API |
| Push Notifications | Firebase Cloud Messaging | Admin SDK |
| Object Storage | MinIO / Cloudflare R2 | S3-compatible |
| Web Server | Gunicorn | 22 |
| Reverse Proxy | Nginx | Alpine |

## API Base URL

All API endpoints are prefixed with `/api/v1/`. See the root [README.md](../README.md) for the complete endpoint reference.

| Path | App |
|------|-----|
| `/api/v1/auth/` | Accounts (registration, login, OTP, profile) |
| `/api/v1/addresses/` | Address management (buyer-only) |
| `/api/v1/products/` | Product listings (public browse, merchant CRUD) |
| `/api/v1/merchants/` | Merchant profiles and product management |
| `/api/v1/cart/` | Shopping cart (buyer-only) |
| `/api/v1/checkout/` | Checkout (buyer-only) |
| `/api/v1/orders/` | Order management (buyer + merchant) |
| `/api/v1/orders/<id>/pay/` | Payment initiation |
| `/api/v1/orders/<id>/payment-status/` | Payment status check |
| `/api/v1/orders/<id>/contract/` | Rental contract |
| `/api/v1/orders/<id>/contract/sign/` | Contract signing |
| `/api/v1/notifications/` | Notifications (list, read, unread count) |
| `/webhooks/snippe/` | Snippe payment webhook (no auth) |

## Response Envelope

Every API response uses a consistent envelope format:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "page": 1, "per_page": 25, "total_pages": 3 }
}
```

On error:

```json
{
  "success": false,
  "data": null,
  "error": { "code": "invalid_credentials", "message": "Invalid email or password." },
  "meta": null
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `dev-insecure-key-change-in-prod` |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `*` |
| `POSTGRES_DB` | Database name | `mes_db` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | (required) |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SNIPPE_API_KEY` | Snippe payment gateway key | (required for payments) |
| `SNIPPE_WEBHOOK_SECRET` | Snippe webhook HMAC secret | (required for webhooks) |
| `SNIPPE_WEBHOOK_URL` | Public webhook URL | (required for payments) |
| `SENDAFRICA_API_KEY` | SendAfrica SMS API key | (required for OTP/SMS) |
| `FIREBASE_CREDENTIALS_JSON` | Path to Firebase credentials file | (optional, for push) |
| `MINIO_ENDPOINT` | MinIO/R2 endpoint | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO/R2 access key | `minioadmin` |
| `MINIO_SECRET_KEY` | MinIO/R2 secret key | `minioadmin` |
| `MINIO_BUCKET_NAME` | Storage bucket name | `mes-uploads` |

## Management Commands

```bash
# Seed database with realistic test data
docker compose exec api python manage.py seed_data

# Create superuser
docker compose exec api python manage.py createsuperuser

# Run migrations
docker compose exec api python manage.py migrate
```

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `nginx` | 80 | Reverse proxy, static file serving |
| `api` | 8000 | Django application (Gunicorn, 3 workers) |
| `db` | 5433 | PostgreSQL 16 (Alpine) |
| `redis` | 6380 | Redis 7 (Alpine) |
| `celery` | — | Celery worker (background tasks) |

## Testing

```bash
# Run the full end-to-end test
docker compose exec api python manage.py shell < test_e2e.py

# Or run manually
python test_e2e.py
```

The E2E test covers: registration, login, OTP, product creation, cart, checkout, payment, webhook, contract signing, order status transitions, notifications, and cleanup.

## License

Built by **DIT — Dar es Salaam Institute of Technology**
