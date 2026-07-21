# Medical Equipment Sharing (MES) — REST API

A full-stack Django REST API for a medical equipment rental marketplace built for healthcare facilities in Tanzania. Hospitals and clinics (buyers) rent equipment from verified vendors (merchants) through a mobile money payment flow with legally binding digital contracts.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Getting Started](#getting-started)
5. [API Reference](#api-reference)
6. [Data Models](#data-models)
7. [Authentication & Authorization](#authentication--authorization)
8. [Business Logic & Workflows](#business-logic--workflows)
9. [External Integrations](#external-integrations)
10. [Deployment](#deployment)
11. [Environment Variables](#environment-variables)
12. [Testing](#testing)
13. [Database Schema](#database-schema)

---

## Architecture Overview

```
┌─────────────┐     ┌─────────┐     ┌──────────────┐
│  Mobile App  │────▶│  Nginx  │────▶│  Django API  │
│  (Flutter /  │     │  :80    │     │  (Gunicorn)  │
│  React Native│     └─────────┘     │  :8000       │
│  / Swift)    │                     └──────┬───────┘
└─────────────┘                            │
                                    ┌──────┴───────┐
                                    │              │
                              ┌─────▼─────┐  ┌────▼────┐
                              │ PostgreSQL │  │  Redis   │
                              │ :5433      │  │ :6380   │
                              └───────────┘  └────┬────┘
                                                  │
                                            ┌─────▼──────┐
                                            │   Celery    │
                                            │   Worker    │
                                            └────────────┘

External Services:
  ├── Snippe (Payment Gateway)  ── USSD mobile money
  ├── SendAfrica (SMS)          ── OTP verification, notifications
  ├── Firebase Cloud Messaging  ── Push notifications
  └── MinIO / Cloudflare R2     ── File storage (PDFs, images)
```

**Request flow:**
1. Mobile app sends HTTP request to Nginx (port 80)
2. Nginx proxies to Gunicorn (port 8000)
3. Django processes request through middleware stack
4. JWT authentication validates the Bearer token
5. View dispatches to appropriate service function
6. Service executes business logic, interacts with database
7. Response wrapped in envelope format and returned

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | Django | 5.1 | Web framework, ORM, admin |
| **API** | Django REST Framework | 3.15 | Serialization, views, permissions |
| **Auth** | SimpleJWT | 5.3 | JWT access + refresh tokens |
| **Database** | PostgreSQL | 16 | Primary data store |
| **Cache** | Redis | 7 | OTP storage, session cache |
| **Task Queue** | Celery | 5.4 | Background task processing |
| **PDF Generation** | ReportLab | 4.2 | Rental agreement PDFs |
| **SMS** | SendAfrica | REST API | OTP codes, notifications |
| **Payments** | Snippe | REST API | USSD mobile money (M-Pesa, TigoPesa, Airtel Money) |
| **Push** | Firebase Cloud Messaging | Admin SDK | Mobile push notifications |
| **Storage** | MinIO / Cloudflare R2 | S3-compatible | Object storage for files |
| **Web Server** | Gunicorn | 22 | WSGI HTTP server |
| **Reverse Proxy** | Nginx | Alpine | Static files, load balancing |
| **Container** | Docker | Compose | Multi-service orchestration |

---

## Project Structure

```
MES-API/
├── README.md                    ← You are here (comprehensive API docs)
└── mes-backend/
    ├── README.md                ← Backend-specific documentation
    ├── config/                  ← Django project configuration
    │   ├── README.md            ← Config documentation
    │   ├── __init__.py          ← Celery app import
    │   ├── celery.py            ← Celery application setup
    │   ├── settings/
    │   │   ├── base.py          ← All settings (DB, cache, JWT, external APIs)
    │   │   ├── dev.py           ← Development (inherits base)
    │   │   └── prod.py          ← Production (DEBUG=False, strict hosts)
    │   ├── urls.py              ← Root URL router (maps prefixes to apps)
    │   ├── wsgi.py              ← WSGI entry point (Gunicorn loads this)
    │   └── asgi.py              ← ASGI entry point (for async)
    ├── apps/
    │   ├── core/                ← Shared framework
    │   │   ├── README.md        ← Core documentation
    │   │   ├── responses.py     ← envelope_ok() / envelope_error()
    │   │   ├── exceptions.py    ← Custom DRF exception handler
    │   │   ├── pagination.py    ← MesPagination (25/page, max 200)
    │   │   ├── permissions.py   ← IsBuyer, IsMerchant, IsOwnerMerchant
    │   │   └── management/commands/
    │   │       └── seed_data.py ← Database seeder (13 products, 6 users)
    │   ├── accounts/            ← Authentication & user management
    │   │   ├── README.md        ← Accounts documentation
    │   │   ├── models.py        ← Account (custom user model)
    │   │   ├── serializers.py   ← Register, Login, Profile serializers
    │   │   ├── views.py         ← Auth endpoints (9 views)
    │   │   ├── urls.py          ← /api/v1/auth/* routes
    │   │   └── services.py      ← Business logic (register, login, OTP, etc.)
    │   ├── addresses/           ← Address management
    │   │   ├── README.md        ← Addresses documentation
    │   │   ├── models.py        ← Address model
    │   │   ├── serializers.py   ← AddressSerializer
    │   │   ├── views.py         ← CRUD views (buyer-only)
    │   │   ├── urls.py          ← /api/v1/addresses/* routes
    │   │   └── services.py      ← Address operations + default handling
    │   ├── equipment/           ← Product catalog
    │   │   ├── README.md        ← Equipment documentation
    │   │   ├── models.py        ← Product, ProductImage, AvailabilityBlock
    │   │   ├── serializers.py   ← List/Detail/Create serializers
    │   │   ├── views.py         ← Product CRUD + merchant views
    │   │   ├── urls.py          ← /api/v1/products/*, /api/v1/merchants/* routes
    │   │   └── services.py      ← Product operations + search/filter
    │   ├── cart/                ← Shopping cart
    │   │   ├── README.md        ← Cart documentation
    │   │   ├── models.py        ← Cart, CartLine
    │   │   ├── serializers.py   ← Cart/Line/CartSync serializers
    │   │   ├── views.py         ← Cart GET/PATCH
    │   │   ├── urls.py          ← /api/v1/cart/* routes
    │   │   └── services.py      ← Cart operations + validation
    │   ├── bookings/            ← Order management
    │   │   ├── README.md        ← Bookings documentation
    │   │   ├── models.py        ← OrderGroup, SubOrder, SubOrderLine
    │   │   ├── serializers.py   ← Checkout/Order/Status serializers
    │   │   ├── views.py         ← Checkout, orders, status update
    │   │   ├── urls.py          ← /api/v1/checkout/*, /api/v1/orders/* routes
    │   │   └── services.py      ← Checkout flow + status state machine
    │   ├── payments/            ← Payment processing
    │   │   ├── README.md        ← Payments documentation
    │   │   ├── models.py        ← PaymentIntent, WebhookEvent
    │   │   ├── serializers.py   ← Payment/Webhook serializers
    │   │   ├── views.py         ← Pay, PaymentStatus views
    │   │   ├── urls.py          ← /api/v1/orders/<id>/pay/* routes
    │   │   ├── webhook_urls.py  ← /webhooks/snippe/* routes
    │   │   ├── webhooks.py      ← Webhook receiver (CSRF-exempt)
    │   │   ├── clients.py       ← SnippeClient (HTTP client)
    │   │   └── services.py      ← Payment logic + webhook handling
    │   ├── contracts/           ← Rental agreements
    │   │   ├── README.md        ← Contracts documentation
    │   │   ├── models.py        ← Contract, Signature
    │   │   ├── serializers.py   ← Contract/Signature serializers
    │   │   ├── views.py         ← Contract retrieval + signing
    │   │   ├── urls.py          ← /api/v1/orders/<id>/contract/* routes
    │   │   └── services.py      ← PDF generation + signing logic
    │   └── notifications/       ← Notifications & push
    │       ├── README.md        ← Notifications documentation
    │       ├── models.py        ← Notification, DeviceToken
    │       ├── serializers.py   ← Notification/Device serializers
    │       ├── views.py         ← List, read, unread count, register device
    │       ├── urls.py          ← /api/v1/notifications/* routes
    │       ├── services.py      ← Notification logic + FCM + SMS
    │       └── clients.py       ← SendAfricaClient (SMS HTTP client)
    ├── manage.py                ← Django management entry point
    ├── test_e2e.py              ← End-to-end integration test
    ├── Dockerfile               ← Python 3.12-slim, Gunicorn
    ├── docker-compose.yml       ← Full stack (5 services)
    ├── nginx.conf               ← Reverse proxy config
    ├── requirements.txt         ← Python dependencies
    ├── .env.example             ← Environment variable template
    └── .dockerignore            ← Docker build exclusions
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git
- (Optional) Python 3.12 for local development

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/troubleman96/MES-API.git
cd MES-API/mes-backend

# 2. Configure environment
cp .env.example .env
# Edit .env with your actual API keys (Snippe, SendAfrica, etc.)

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec api python manage.py migrate

# 5. Seed the database with test data
docker compose exec api python manage.py seed_data

# 6. Verify the API is running
curl http://localhost:8000/api/v1/products/
```

### Local Development Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ensure PostgreSQL and Redis are running locally
# PostgreSQL on port 5433, Redis on port 6380

# 4. Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export REDIS_URL=redis://localhost:6380/1

# 5. Run migrations and start server
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

---

## API Reference

### Base URL

```
http://localhost:8000/api/v1/
```

### Response Envelope

All responses follow a consistent envelope format:

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": null
}
```

**Paginated:**
```json
{
  "success": true,
  "data": {
    "items": [...],
    "count": 150,
    "meta": {
      "page": 1,
      "per_page": 25,
      "total_pages": 6
    }
  }
}
```

**Error:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid email or password."
  },
  "meta": null
}
```

### Authentication

All protected endpoints require a JWT Bearer token:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Token lifetime: 15 minutes (access), 7 days (refresh).

---

### Endpoints

#### 1. Authentication (`/api/v1/auth/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `register/` | No | Create new account |
| POST | `login/` | No | Login with email + password |
| POST | `refresh/` | No | Refresh access token |
| POST | `logout/` | Yes | Invalidate refresh token |
| GET | `me/` | Yes | Get profile |
| PATCH | `me/` | Yes | Update profile |
| POST | `send-phone-otp/` | Yes | Send OTP to phone |
| POST | `verify-phone/` | Yes | Verify phone with OTP |
| POST | `forgot-password/` | No | Request password reset |
| POST | `forgot-password/confirm/` | No | Reset password with OTP |

**POST `/api/v1/auth/register/`**
```json
// Request
{
  "role": "buyer",
  "email": "juma.kitonda@mes.co.tz",
  "password": "SecurePass123!",
  "phone": "0694157749",
  "first_name": "Juma",
  "last_name": "Kitonda",
  "facility_name": "Kitonda Community Health Centre"
}

// Response (201)
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "role": "buyer",
    "profile_complete": true
  }
}
```

**POST `/api/v1/auth/login/`**
```json
// Request
{
  "email": "juma.kitonda@mes.co.tz",
  "password": "SecurePass123!"
}

// Response (200)
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 900,
    "role": "buyer",
    "phone_verified": true,
    "profile_complete": true
  }
}
```

**POST `/api/v1/auth/refresh/`**
```json
// Request
{ "refresh_token": "eyJ..." }

// Response (200)
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```

**POST `/api/v1/auth/send-phone-otp/`**
```json
// Request
{ "phone": "0694157749" }

// Response (200)
{ "success": true, "data": { "message": "OTP sent successfully." } }
```

**POST `/api/v1/auth/verify-phone/`**
```json
// Request
{ "otp": "123456" }

// Response (200)
{ "success": true, "data": { "message": "Phone verified successfully." } }
```

**POST `/api/v1/auth/forgot-password/`**
```json
// Request
{ "email": "juma.kitonda@mes.co.tz" }

// Response (200)
{ "success": true, "data": { "message": "If an account exists, a reset code has been sent." } }
```

**POST `/api/v1/auth/forgot-password/confirm/`**
```json
// Request
{
  "email": "juma.kitonda@mes.co.tz",
  "otp": "123456",
  "new_password": "NewSecurePass123!"
}

// Response (200)
{ "success": true, "data": { "message": "Password reset successfully." } }
```

---

#### 2. Addresses (`/api/v1/addresses/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `addresses/` | Yes | Buyer | List all addresses |
| POST | `addresses/` | Yes | Buyer | Create address |
| PUT | `addresses/<uuid>/` | Yes | Buyer | Update address |
| DELETE | `addresses/<uuid>/` | Yes | Buyer | Delete address |

**POST `/api/v1/addresses/`**
```json
// Request
{
  "label": "Main Facility",
  "facility_name": "Kitonda Community Health Centre",
  "address_line1": "Bagamoyo Road, Upanga",
  "city": "Dar es Salaam",
  "district": "Kinondoni",
  "ward": "Upanga West",
  "contact_name": "Juma Kitonda",
  "contact_phone": "0694157749",
  "address_type": "both",
  "is_default": true
}

// Response (201)
{
  "success": true,
  "data": {
    "id": "uuid...",
    "label": "Main Facility",
    "facility_name": "Kitonda Community Health Centre",
    ...
    "created_at": "2026-07-21T09:00:00+03:00"
  }
}
```

---

#### 3. Products (`/api/v1/products/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `products/` | No | Any | Browse products (paginated, filterable) |
| POST | `products/` | Yes | Merchant | Create product listing |
| GET | `products/<uuid>/` | No | Any | View product detail |
| PUT | `products/<uuid>/` | Yes | Merchant (owner) | Update product |
| DELETE | `products/<uuid>/` | Yes | Merchant (owner) | Soft-delete product |
| GET | `products/<uuid>/availability/` | No | Any | Check blocked date ranges |

**Query parameters:**
- `?category=diagnostic` — Filter by category
- `?search=ultrasound` — Search by name/description
- `?per_page=10` — Items per page (max 200)
- `?page=2` — Page number

**GET `/api/v1/products/`**
```json
// Response (200)
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid...",
        "name": "Portable Ultrasound Scanner GE Vscan Air",
        "category": "diagnostic",
        "daily_rate_tzs": 45000,
        "is_featured": true,
        "is_active": true,
        "created_at": "2026-07-21T09:18:18.913211+03:00",
        "images": [
          {
            "id": "uuid...",
            "url": "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600",
            "sort_order": 0
          },
          {
            "id": "uuid...",
            "url": "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=600",
            "sort_order": 1
          }
        ]
      }
    ],
    "count": 13,
    "meta": { "page": 1, "per_page": 25, "total_pages": 1 }
  }
}
```

**POST `/api/v1/products/`** (Merchant only)
```json
// Request
{
  "name": "Digital Stethoscope 3M Littmann",
  "category": "diagnostic",
  "description": "Professional-grade digital stethoscope...",
  "specs": { "brand": "3M", "model": "CORE 500", "weight_kg": 0.35 },
  "daily_rate_tzs": 15000,
  "is_featured": false
}

// Response (201)
{ "success": true, "data": { "id": "uuid...", "name": "Digital Stethoscope...", ... } }
```

**GET `/api/v1/products/<uuid>/`**
```json
// Response (200)
{
  "success": true,
  "data": {
    "id": "uuid...",
    "merchant": "uuid...",
    "merchant_name": "MedEquip Tanzania Ltd",
    "name": "Digital Stethoscope 3M Littmann",
    "category": "diagnostic",
    "description": "Professional-grade digital stethoscope...",
    "specs": { "brand": "3M", "model": "CORE 500" },
    "daily_rate_tzs": 15000,
    "is_featured": false,
    "is_active": true,
    "images": [...]
  }
}
```

---

#### 4. Merchants (`/api/v1/merchants/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `merchants/<uuid>/` | No | Any | View merchant profile |
| GET | `merchants/me/products/` | Yes | Merchant | List own products |

---

#### 5. Cart (`/api/v1/cart/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `cart/` | Yes | Buyer | Get current cart |
| PATCH | `cart/` | Yes | Buyer | Replace entire cart |

**GET `/api/v1/cart/`**
```json
// Response (200)
{
  "success": true,
  "data": {
    "account": "uuid...",
    "lines": [
      {
        "id": "uuid...",
        "product": "uuid...",
        "product_name": "Digital Stethoscope 3M Littmann",
        "daily_rate_tzs": 15000,
        "rental_start": "2026-07-25",
        "rental_end": "2026-07-28",
        "quantity": 1,
        "added_at": "2026-07-21T10:00:00+03:00"
      }
    ],
    "updated_at": "2026-07-21T10:00:00+03:00"
  }
}
```

**PATCH `/api/v1/cart/`** (Replace entire cart)
```json
// Request
{
  "lines": [
    {
      "product": "uuid-of-product",
      "rental_start": "2026-07-25",
      "rental_end": "2026-07-28",
      "quantity": 1
    }
  ]
}

// Response (200) — may include stale_lines if some items failed validation
{
  "success": true,
  "data": {
    "cart": { "lines": [...], "updated_at": "..." },
    "stale_lines": []
  }
}
```

---

#### 6. Checkout & Orders (`/api/v1/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `checkout/` | Yes | Buyer | Convert cart to order |
| GET | `orders/` | Yes | Buyer/Merchant | List orders |
| GET | `orders/<uuid>/` | Yes | Buyer/Merchant | View order detail |
| PATCH | `orders/<uuid>/status/` | Yes | Merchant | Update order status |

**POST `/api/v1/checkout/`**
```json
// Request
{
  "delivery_address_id": "uuid-of-address",
  "billing_address_id": "uuid-of-address",
  "notes": "Please deliver before 10 AM"
}

// Response (201)
{
  "success": true,
  "data": {
    "order_group_id": "uuid...",
    "sub_orders": [
      {
        "id": "uuid...",
        "merchant_name": "MedEquip Tanzania Ltd",
        "subtotal_tzs": 45000,
        "status": "pending_payment"
      }
    ]
  }
}
```

**GET `/api/v1/orders/`**
```json
// Response (200) — buyer sees their orders, merchant sees incoming
{
  "success": true,
  "data": [
    {
      "id": "uuid...",
      "merchant_name": "MedEquip Tanzania Ltd",
      "subtotal_tzs": 45000,
      "status": "confirmed",
      "created_at": "2026-07-21T09:18:20.634165+03:00"
    }
  ]
}
```

**Query parameters:**
- `?status=confirmed` — Filter by status

**PATCH `/api/v1/orders/<uuid>/status/`** (Merchant only)
```json
// Request
{ "status": "dispatched" }

// Response (200)
{
  "success": true,
  "data": {
    "id": "uuid...",
    "status": "dispatched",
    ...
  }
}
```

**Order status transitions:**
```
pending_payment → confirmed    (payment completed)
pending_payment → cancelled    (merchant cancels)
confirmed       → dispatched   (requires signed contract)
dispatched      → delivered    (equipment delivered)
delivered       → return_due   (return deadline approaching)
delivered       → returned     (equipment returned)
return_due      → returned     (equipment returned)
```

---

#### 7. Payments (`/api/v1/orders/<uuid>/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `orders/<uuid>/pay/` | Yes | Buyer | Initiate payment |
| GET | `orders/<uuid>/payment-status/` | Yes | Buyer/Merchant | Check payment status |

**POST `/api/v1/orders/<uuid>/pay/`**
```json
// Response (201)
{
  "success": true,
  "data": {
    "id": "uuid...",
    "sub_order": "uuid...",
    "snippe_reference": "snp_ref_123...",
    "status": "pending",
    "amount_tzs": 45000,
    "network": "",
    "failure_reason": "",
    "expires_at": "2026-07-21T13:18:20+03:00",
    "created_at": "2026-07-21T09:18:20+03:00"
  }
}
```

**Webhook endpoint:** `POST /webhooks/snippe/`

Snippe sends payment status updates to this endpoint. The webhook is verified using HMAC-SHA256 signature.

---

#### 8. Contracts (`/api/v1/orders/<uuid>/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `orders/<uuid>/contract/` | Yes | Buyer/Merchant | Retrieve rental agreement |
| POST | `orders/<uuid>/contract/sign/` | Yes | Buyer | Sign the contract |

**GET `/api/v1/orders/<uuid>/contract/`**
```json
// Response (200)
{
  "success": true,
  "data": {
    "id": "uuid...",
    "sub_order": "uuid...",
    "pdf_url": "contracts/uuid/agreement.pdf",
    "signatures": [],
    "generated_at": "2026-07-21T09:19:00+03:00"
  }
}
```

**POST `/api/v1/orders/<uuid>/contract/sign/`**
```json
// Request
{
  "signature_image_url": "https://storage.mes.co.tz/signatures/buyer123.png"
}

// Response (201)
{
  "success": true,
  "data": {
    "message": "Contract signed successfully.",
    "signature_id": "uuid..."
  }
}
```

---

#### 9. Notifications (`/api/v1/notifications/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `notifications/` | Yes | List all notifications |
| GET | `notifications/unread-count/` | Yes | Get unread count |
| PATCH | `notifications/<uuid>/read/` | Yes | Mark as read |
| POST | `notifications/read-all/` | Yes | Mark all as read |
| POST | `notifications/register-device/` | Yes | Register FCM token |

**GET `/api/v1/notifications/`**
```json
// Response (200)
{
  "success": true,
  "data": [
    {
      "id": "uuid...",
      "type": "order_confirmed",
      "title": "Order Confirmed",
      "body": "Your order has been confirmed by MedEquip Tanzania.",
      "read_at": null,
      "created_at": "2026-07-21T09:19:00+03:00"
    }
  ]
}
```

**POST `/api/v1/notifications/register-device/`**
```json
// Request
{ "fcm_token": "dKx4...firebase_token..." }

// Response (201)
{ "success": true, "data": { "message": "Device registered.", "id": "uuid..." } }
```

---

## Data Models

### Entity Relationship Diagram

```
Account (users)
├── Address (delivery/billing addresses)
├── Product (equipment listings)
│   ├── ProductImage (product photos)
│   └── AvailabilityBlock (booked/maintenance dates)
├── Cart
│   └── CartLine (cart items)
├── OrderGroup (checkout transactions)
│   ├── Address (delivery_address)
│   ├── Address (billing_address)
│   └── SubOrder (per-merchant order)
│       ├── Account (merchant)
│       ├── SubOrderLine (line items)
│       │   └── Product (snapshotted)
│       ├── PaymentIntent (payment tracking)
│       ├── Contract (rental agreement)
│       │   └── Signature (digital signatures)
│       └── AvailabilityBlock (booked dates)
├── Notification (in-app messages)
├── DeviceToken (FCM push tokens)
└── WebhookEvent (idempotency tracker)
```

### Model Summary

| Model | Table | Records | Description |
|-------|-------|---------|-------------|
| `Account` | `accounts` | Users | Custom user model (buyer/merchant) |
| `Address` | `addresses` | Addresses | Delivery and billing addresses |
| `Product` | `products` | Equipment | Equipment listings |
| `ProductImage` | `product_images` | Images | Product photos (URLs) |
| `AvailabilityBlock` | `availability_blocks` | Blocks | Booked/maintenance date ranges |
| `Cart` | `carts` | Carts | One per buyer |
| `CartLine` | `cart_lines` | Items | Items in a cart |
| `OrderGroup` | `order_groups` | Orders | Checkout transactions |
| `SubOrder` | `sub_orders` | Sub-orders | Per-merchant order portions |
| `SubOrderLine` | `sub_order_lines` | Lines | Individual rental line items |
| `PaymentIntent` | `payment_intents` | Payments | Snippe payment tracking |
| `WebhookEvent` | `webhook_events` | Events | Webhook idempotency |
| `Contract` | `contracts` | Contracts | Rental agreements |
| `Signature` | `signatures` | Signatures | Digital contract signatures |
| `Notification` | `notifications` | Notifications | In-app messages |
| `DeviceToken` | `device_tokens` | Devices | FCM push token registrations |

---

## Authentication & Authorization

### JWT Authentication

- **Access token:** 15-minute lifetime, used for API requests
- **Refresh token:** 7-day lifetime, used to obtain new access tokens
- **Rotation:** Refresh tokens are rotated on each use (new pair issued)
- **Format:** `Authorization: Bearer <access_token>`

### Role-Based Access Control

| Permission | Logic | Used By |
|-----------|-------|---------|
| `AllowAny` | No auth required | Product listing, login, register |
| `IsAuthenticated` | Valid JWT required | All protected endpoints |
| `IsBuyer` | `role == "buyer"` | Cart, addresses, checkout, order list |
| `IsMerchant` | `role == "merchant"` | Product CRUD, order status updates |
| `IsOwnerMerchant` | `obj.merchant_id == user.id` | Product update/delete |

### Authorization Matrix

| Endpoint | Buyer | Merchant | Anonymous |
|----------|-------|----------|-----------|
| Register / Login | Yes | Yes | Yes |
| Browse products | Yes | Yes | Yes |
| Create product | No | Yes | No |
| Update/Delete product | No | Owner only | No |
| Manage addresses | Yes | No | No |
| Cart operations | Yes | No | No |
| Checkout | Yes | No | No |
| View orders | Own orders | Incoming orders | No |
| Update order status | No | Own orders | No |
| Initiate payment | Yes | No | No |
| View contracts | Own orders | Own orders | No |
| Sign contract | Buyer only | No | No |
| Notifications | Own | Own | No |

---

## Business Logic & Workflows

### 1. Registration & Onboarding

```
1. Buyer registers with email, password, phone, facility_name
2. Merchant registers with email, password, phone, business_name
3. User receives JWT tokens
4. User sends OTP to phone via /send-phone-otp/
5. User verifies OTP via /verify-phone/
6. Phone is now verified (required for checkout)
```

### 2. Product Catalog

```
1. Merchant creates product with name, category, description, specs, daily_rate_tzs
2. Product images are attached (URLs)
3. Product appears in public catalog
4. Buyers can browse, filter by category, search by name
5. Merchant can update or soft-delete their own products
```

### 3. Shopping Cart

```
1. Buyer adds items to cart (PATCH /cart/ with full desired state)
2. Server validates each item:
   - Product exists and is active
   - Rental start < rental end
   - No availability conflict (no overlapping bookings)
   - Price matches current price
3. Invalid items returned as stale_lines with reasons
4. Buyer reviews cart before checkout
```

### 4. Checkout & Order Creation

```
1. Buyer calls POST /checkout/ with delivery + billing address IDs
2. Server verifies:
   - Phone is verified
   - Addresses exist and belong to buyer
   - Cart is non-empty
   - All products active
   - No availability conflicts (with row locking)
3. Creates OrderGroup + SubOrder per merchant + SubOrderLines
4. Creates AvailabilityBlocks for each rented item
5. Clears cart
6. Returns order summary
```

### 5. Payment

```
1. Buyer calls POST /orders/<id>/pay/
2. Server creates PaymentIntent and calls Snippe API
3. Snippe sends USSD prompt to buyer's phone
4. Buyer completes payment on phone
5. Snippe sends webhook to /webhooks/snippe/
6. Server verifies HMAC signature
7. On payment.completed:
   - PaymentIntent.status → completed
   - SubOrder.status → confirmed
   - Contract PDF is generated
8. On payment.failed/expired:
   - PaymentIntent.status → failed/expired
   - SubOrder.status → payment_failed
```

### 6. Contract & Dispatch

```
1. Contract PDF is auto-generated after payment confirmation
2. Buyer retrieves contract via GET /orders/<id>/contract/
3. Buyer signs contract via POST /orders/<id>/contract/sign/
4. Merchant can now dispatch (status → dispatched)
   (dispatch requires signed contract)
5. Merchant marks as delivered (status → delivered)
6. Equipment rental period begins
7. After rental period, merchant can mark return
```

### 7. Order Status State Machine

```
                  ┌──────────────────┐
                  │ pending_payment  │
                  └────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
        ┌───────────┐           ┌────────────┐
        │ confirmed │           │ cancelled  │
        └─────┬─────┘           └────────────┘
              │ (requires signed contract)
              ▼
        ┌───────────┐
        │ dispatched│
        └─────┬─────┘
              │
              ▼
        ┌───────────┐
        │ delivered │
        └─────┬─────┘
              │
        ┌─────┴─────┐
        ▼           ▼
  ┌───────────┐ ┌──────────┐
  │ return_due│ │ returned │
  └─────┬─────┘ └──────────┘
        │
        ▼
  ┌──────────┐
  │ returned │
  └──────────┘
```

---

## External Integrations

### Snippe Payment Gateway

- **API:** `https://api.snippe.sh/v1/payments`
- **Auth:** Bearer token (`SNIPPE_API_KEY`)
- **Payment type:** USSD mobile money (M-Pesa, TigoPesa, Airtel Money)
- **Webhook:** HMAC-SHA256 signature verification
- **Idempotency:** `Idempotency-Key` header on payment initiation

### SendAfrica SMS

- **API:** `https://api.sendafrica.online/v1/sms/`
- **Auth:** `X-API-Key` header (`SENDAFRICA_API_KEY`)
- **Use cases:** OTP verification codes, password reset codes, order notifications

### Firebase Cloud Messaging (FCM)

- **SDK:** `firebase-admin` Python SDK
- **Use case:** Push notifications to mobile devices
- **Flow:** Device registers FCM token → server sends multicast messages

### MinIO / Cloudflare R2

- **Protocol:** S3-compatible API
- **Use case:** File storage for contract PDFs, signature images, product photos
- **Configuration:** `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET_NAME`

---

## Deployment

### Docker Compose Services

| Service | Image | Port | Command | Description |
|---------|-------|------|---------|-------------|
| `nginx` | nginx:alpine | 80 | — | Reverse proxy, static files |
| `api` | mes-backend-api | 8000 | gunicorn (3 workers) | Django application |
| `db` | postgres:16-alpine | 5433→5432 | — | PostgreSQL database |
| `redis` | redis:7-alpine | 6380→6379 | — | Cache + Celery broker |
| `celery` | mes-backend-celery | — | celery worker | Background tasks |

### Volumes

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Database persistence |
| `redis_data` | Cache persistence |
| `static_files` | Django static files |
| `media_files` | Uploaded media |

### Nginx Configuration

```nginx
upstream api {
    server api:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Production Deployment

```bash
# 1. Set production environment
export DJANGO_SETTINGS_MODULE=config.settings.prod

# 2. Run with Docker Compose
docker compose -f docker-compose.yml up -d

# 3. Run migrations
docker compose exec api python manage.py migrate

# 4. Create admin user
docker compose exec api python manage.py createsuperuser

# 5. Seed data (optional)
docker compose exec api python manage.py seed_data
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes | `dev-insecure-key-change-in-prod` | Django secret key |
| `DEBUG` | No | `True` | Debug mode |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated hostnames |
| `POSTGRES_DB` | No | `mes_db` | Database name |
| `POSTGRES_USER` | No | `postgres` | Database user |
| `POSTGRES_PASSWORD` | Yes | — | Database password |
| `POSTGRES_HOST` | No | `localhost` | Database host |
| `POSTGRES_PORT` | No | `5432` | Database port |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection |
| `SNIPPE_API_KEY` | For payments | — | Snippe gateway key |
| `SNIPPE_WEBHOOK_SECRET` | For webhooks | — | Webhook HMAC secret |
| `SNIPPE_WEBHOOK_URL` | For payments | — | Public webhook URL |
| `SENDAFRICA_API_KEY` | For SMS | — | SendAfrica API key |
| `FIREBASE_CREDENTIALS_JSON` | For push | — | Firebase credentials path |
| `MINIO_ENDPOINT` | For storage | `localhost:9000` | MinIO/R2 endpoint |
| `MINIO_ACCESS_KEY` | For storage | `minioadmin` | Storage access key |
| `MINIO_SECRET_KEY` | For storage | `minioadmin` | Storage secret key |
| `MINIO_BUCKET_NAME` | For storage | `mes-uploads` | Storage bucket |

---

## Testing

### End-to-End Test

The `test_e2e.py` script tests the complete rental lifecycle:

1. Register buyer account
2. Register merchant account
3. Login both accounts
4. Send OTP to buyer phone
5. Verify buyer phone
6. Send OTP to merchant phone
7. Verify merchant phone
8. Merchant creates product listing
9. Buyer creates address
10. Buyer adds item to cart
11. Buyer checks out (cart → order)
12. Buyer initiates payment
13. Simulate payment webhook
14. Check contract generated
15. Buyer signs contract
16. Merchant confirms order
17. Merchant dispatches order
18. Check notifications created
19. Merchant delivers
20. Check order lists
21. Register device token
22. Cleanup test data

```bash
# Run via Docker
docker compose exec api python test_e2e.py

# Or locally
python test_e2e.py
```

### Seed Data

```bash
# Seed with realistic test data
docker compose exec api python manage.py seed_data

# Creates: 3 buyers, 3 merchants, 13 products, 3 orders
# All passwords: TestPass123!
```

### Database Reset

```bash
# Full reset
docker compose exec api python manage.py flush --no-input
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_data
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8
- Use the service layer pattern (views → services → models)
- All responses must use the envelope format (`envelope_ok` / `envelope_error`)
- All endpoints must use DRF serializers for input validation
- UUID primary keys for all models
- Foreign keys use `PROTECT` to prevent accidental deletion of referenced records

---

## License

Built by **DIT — Dar es Salaam Institute of Technology**
