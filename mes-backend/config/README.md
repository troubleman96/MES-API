# config/ — Django Project Configuration

This directory contains the Django project-level configuration: settings, URL routing, WSGI/ASGI entry points, and Celery setup.

---

## File Inventory

### `config/__init__.py` (3 lines)

Imports the Celery application instance from `config.celery` and exports it via `__all__`. This ensures Celery is loaded when Django starts, enabling background task execution.

```python
from .celery import app as celery_app
__all__ = ("celery_app",)
```

### `config/celery.py` (9 lines)

Creates and configures the Celery application instance.

**Object:** `app` — Celery instance named `"mes_backend"`.

**Configuration:**
- Reads settings from `os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.dev")`
- Uses the `CELERY` namespace for configuration
- Auto-discovers tasks from all installed apps (`autodiscover_tasks()`)

### `config/urls.py` (15 lines)

Root URL configuration for the entire API. Maps top-level URL prefixes to their respective Django apps.

**URL Patterns:**

| Pattern | Target | Description |
|---------|--------|-------------|
| `admin/` | `admin.site.urls` | Django admin panel |
| `api/v1/auth/` | `apps.accounts.urls` | Authentication endpoints |
| `api/v1/addresses/` | `apps.addresses.urls` | Address management |
| `api/v1/` | `apps.equipment.urls` | Products and merchants |
| `api/v1/cart/` | `apps.cart.urls` | Shopping cart |
| `api/v1/` | `apps.bookings.urls` | Checkout and orders |
| `api/v1/orders/` | `apps.payments.urls` | Payment initiation |
| `api/v1/` | `apps.contracts.urls` | Rental contracts |
| `api/v1/notifications/` | `apps.notifications.urls` | Notifications |
| `webhooks/` | `apps.payments.webhook_urls` | External webhooks (Snippe) |

### `config/settings/base.py` (146 lines)

Base Django settings shared across all environments. This is the central configuration file.

**Key Settings:**

| Setting | Value | Purpose |
|---------|-------|---------|
| `SECRET_KEY` | From env | Django cryptographic signing |
| `DEBUG` | From env (default: `True`) | Debug mode toggle |
| `ALLOWED_HOSTS` | From env (default: `*`) | Host validation |
| `AUTH_USER_MODEL` | `"accounts.Account"` | Custom user model |
| `AUTH_PASSWORD_VALIDATORS` | 4 validators | Password strength enforcement |
| `TIME_ZONE` | `"Africa/Dar_es_Salaam"` | Tanzanian timezone |
| `USE_TZ` | `True` | Enable timezone-aware datetimes |
| `DEFAULT_AUTO_FIELD` | `"django.db.models.BigAutoField"` | UUID-compatible PKs |

**Installed Apps (14):**
- Django core: `admin`, `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles`
- Third-party: `rest_framework`, `rest_framework_simplejwt`, `corsheaders`
- Custom apps: `core`, `accounts`, `addresses`, `equipment`, `cart`, `bookings`, `payments`, `contracts`, `notifications`

**Middleware (9):**
1. `SecurityMiddleware` — HTTPS/HSTS enforcement
2. `WhiteNoiseMiddleware` — Static file serving
3. `CorsMiddleware` — CORS headers
4. `SessionMiddleware` — Session handling
5. `CommonMiddleware` — URL normalization, content-length
6. `CsrfViewMiddleware` — CSRF protection
7. `AuthenticationMiddleware` — User session binding
8. `MessageMiddleware` — Flash messages
9. `XFrameOptionsMiddleware` — Clickjacking protection

**Database:**
- Engine: PostgreSQL (via `psycopg2-binary`)
- Reads host/port/user/password/name from environment variables

**REST Framework:**
- Authentication: JWT (Bearer token)
- Pagination: Custom `MesPagination` (25 items/page, max 200)
- Exception handler: Custom `mes_exception_handler` (envelope format)

**JWT Configuration:**
- Access token lifetime: 15 minutes
- Refresh token lifetime: 7 days
- Rotate refresh tokens: enabled
- Blacklist after rotation: disabled

**Cache:**
- Backend: Redis (`django.core.cache.backends.redis.RedisCache`)
- Used for: OTP storage (15 min TTL), session caching

**Celery:**
- Broker: Redis (port 6379/0)
- Backend: Redis (port 6379/0)
- Serializer: JSON

**External Services (from env):**
- `SNIPPE_API_KEY`, `SNIPPE_WEBHOOK_SECRET`, `SNIPPE_WEBHOOK_URL`
- `SENDAFRICA_API_KEY`
- `FIREBASE_CREDENTIALS_JSON`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_NAME`

### `config/settings/dev.py` (1 line)

Development settings. Imports everything from `base.py` with no overrides.

```python
from .base import *  # noqa: F401,F403
```

### `config/settings/prod.py` (4 lines)

Production settings. Inherits from `base.py` with overrides:

| Setting | Value | Purpose |
|---------|-------|---------|
| `DEBUG` | `False` | Disable debug mode |
| `ALLOWED_HOSTS` | From env (required) | Restrict allowed hosts |

### `config/wsgi.py` (7 lines)

WSGI entry point for production deployment (Gunicorn). Sets `DJANGO_SETTINGS_MODULE` to `config.settings.prod`.

**Object:** `application` — WSGI application instance.

### `config/asgi.py` (7 lines)

ASGI entry point for async deployment. Sets `DJANGO_SETTINGS_MODULE` to `config.settings.prod`.

**Object:** `application` — ASGI application instance.

---

## How This Directory Connects to the App

- `config/urls.py` is the **routing hub** — it directs every incoming HTTP request to the correct Django app based on URL prefix.
- `config/settings/base.py` is the **configuration hub** — it wires together all apps, middleware, database, cache, and external services.
- `config/celery.py` enables **background task processing** — used by Celery for async jobs (SMS delivery, email, etc.).
- `config/wsgi.py` is the **deployment entry point** — Gunicorn loads this to serve the application.
