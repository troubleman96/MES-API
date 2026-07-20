# MES Django Backend — DRF Specification
### Scoped to exactly what the Kotlin app in `KOTLIN.md` calls. Nothing more, nothing less.

**Companion document to:** `KOTLIN.md` (client) — every endpoint below exists because a specific
Kotlin `Retrofit` interface or repository call in that document needs it. Every model field exists
because a specific Compose screen renders it. If you're tempted to add a field or endpoint that isn't
traceable to something in `KOTLIN.md`, it doesn't belong in v1 — add it to `context/decisions.md`
during the build instead, as a deferred idea, not into the running spec.

---

## 0. Scope Discipline

### 0.1 What's in

Nine apps, each owning one domain, each a self-contained "service" (models + serializers + a
`services.py` business-logic layer + thin views + urls) — this is the "Django apps-as-services"
convention applied literally, one app per bounded context, no app reaching into another app's models
directly (cross-app reads go through that app's `services.py`, never raw ORM queries into a foreign
app).

| App | Owns | Kotlin modules that call it |
|---|---|---|
| `core` | Response envelope, pagination, exceptions, base permissions — no models of its own | every `feature-*` module, indirectly |
| `accounts` | Register, login, session, role, phone verification | `feature-auth` |
| `addresses` | Buyer's saved address book | `feature-checkout`, `feature-profile` |
| `equipment` | Product catalogue, merchant listings, availability | `feature-catalog`, `feature-merchant` |
| `cart` | Server-synced cart mirror of the Room cart | `feature-cart` |
| `bookings` | Checkout → sub-orders, fulfillment status | `feature-checkout`, `feature-orders`, `feature-merchant` |
| `payments` | Snippe payment intents + webhook | `feature-checkout` (via `bookings`) |
| `contracts` | Auto-generated agreement + e-signature | `feature-checkout`, `feature-orders` |
| `notifications` | In-app notification center, FCM registration, fan-out (incl. SendAfrica SMS trigger) | `feature-notifications`, every domain event |

### 0.2 What's deliberately NOT built

No admin analytics dashboard, no CMS for marketing content, no separate "categories" table (categories
are a fixed `choices=` field on `Product` — the catalog rail in §4.3 of `KOTLIN.md` needs six labels,
not a manageable taxonomy), no merchant subscription/billing enforcement logic (the SRS lists it as a
future revenue stream — nothing in `KOTLIN.md`'s screens reads or writes it, so it's out until a screen
needs it), no separate reviews/ratings system (the merchant trust card in §3.3 shows `is_verified`, not
a computed rating — don't build a ratings pipeline nobody asked the client to render), no wishlist/
favorites (never appears in `KOTLIN.md`). If it isn't called from a Kotlin repository, it isn't here.

### 0.3 Response envelope — shared across every app, defined once

Matches exactly what `core-network/Envelope.kt` parses in `KOTLIN.md` §9 — this is not negotiable per
app, every view returns this shape via the shared renderer in `core`:

```python
# apps/core/responses.py
from rest_framework.response import Response

def envelope_ok(data=None, meta=None, status=200):
    return Response({"success": True, "data": data, "error": None, "meta": meta}, status=status)

def envelope_error(code: str, message: str, status=400):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message}, "meta": None},
        status=status,
    )
```

```python
# apps/core/pagination.py
from rest_framework.pagination import PageNumberPagination

class MesPagination(PageNumberPagination):
    page_size_query_param = "per_page"
    page_size = 25
    max_page_size = 200

    def get_paginated_response(self, data):
        return envelope_ok(
            data={"items": data, "total": self.page.paginator.count},
            meta={
                "page": self.page.number,
                "per_page": self.get_page_size(self.request),
                "total_pages": self.page.paginator.num_pages,
            },
        )
```

```python
# apps/core/exceptions.py — DRF's EXCEPTION_HANDLER, so every unhandled error still returns the envelope
from rest_framework.views import exception_handler

def mes_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return envelope_error("server_error", "Internal server error", status=500)
    code = getattr(exc, "default_code", "error")
    message = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
    return envelope_error(str(code), str(message), status=response.status_code)
```

```python
# apps/core/permissions.py — role gate used by every app below
from rest_framework.permissions import BasePermission

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == "buyer")

class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == "merchant")

class IsOwnerMerchant(BasePermission):
    """Object-level: the requesting merchant owns this product/order."""
    def has_object_permission(self, request, view, obj):
        return obj.merchant_id == request.user.id
```

---

## 1. Project Layout

```
mes-backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py                    # includes each app's urls.py under /api/v1/*
│   ├── asgi.py / wsgi.py
│   └── celery.py
├── apps/
│   ├── core/                      # envelope, pagination, exceptions, permissions — no models
│   │   ├── responses.py
│   │   ├── pagination.py
│   │   ├── exceptions.py
│   │   └── permissions.py
│   ├── accounts/
│   │   ├── models.py              # Account, custom user manager
│   │   ├── serializers.py
│   │   ├── services.py            # register(), verify_phone(), issue_tokens(), refresh()
│   │   ├── views.py
│   │   └── urls.py
│   ├── addresses/
│   │   ├── models.py              # Address
│   │   ├── serializers.py
│   │   ├── services.py            # create_address(), set_default(), delete_address()
│   │   ├── views.py
│   │   └── urls.py
│   ├── equipment/
│   │   ├── models.py              # Product, ProductImage, AvailabilityBlock
│   │   ├── serializers.py
│   │   ├── services.py            # list_products(), check_availability(), create_listing()
│   │   ├── views.py
│   │   └── urls.py
│   ├── cart/
│   │   ├── models.py              # Cart, CartLine
│   │   ├── serializers.py
│   │   ├── services.py            # replace_cart(), validate_lines()
│   │   ├── views.py
│   │   └── urls.py
│   ├── bookings/
│   │   ├── models.py              # OrderGroup, SubOrder
│   │   ├── serializers.py
│   │   ├── services.py            # checkout(), split_into_sub_orders(), update_status()
│   │   ├── views.py
│   │   └── urls.py
│   ├── payments/
│   │   ├── models.py              # PaymentIntent, WebhookEvent
│   │   ├── serializers.py
│   │   ├── services.py            # create_snippe_payment(), verify_webhook_signature()
│   │   ├── clients.py             # SnippeClient — the only file that imports the Snippe API key
│   │   ├── webhooks.py            # POST /webhooks/snippe — not under /api/v1, not client-facing
│   │   ├── views.py
│   │   └── urls.py
│   ├── contracts/
│   │   ├── models.py              # Contract, Signature
│   │   ├── serializers.py
│   │   ├── services.py            # generate_contract_pdf(), record_signature()
│   │   ├── views.py
│   │   └── urls.py
│   └── notifications/
│       ├── models.py              # Notification, DeviceToken
│       ├── serializers.py
│       ├── services.py            # notify(), fan-out to FCM + SendAfrica — the only file that
│       │                          # imports the SendAfrica API key
│       ├── clients.py             # SendAfricaClient
│       ├── views.py
│       └── urls.py
├── manage.py
└── requirements.txt
```

One rule that keeps this from rotting: **`services.py` is the only place business logic lives.**
Views deserialize the request, call one `services.` function, wrap the result in `envelope_ok`/
`envelope_error`. This is the Django-app equivalent of the Go clean-arch `usecase` layer CamelTech
already uses — `services.py` = usecase, `models.py` + the ORM = repository, `views.py` = delivery.

---

## 2. `accounts`

### 2.1 Model

```python
# apps/accounts/models.py
class Account(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid4)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=16, null=True, blank=True)     # E.164, e.g. +255712345678
    phone_verified = models.BooleanField(default=False)
    role = models.CharField(choices=[("buyer", "Buyer"), ("merchant", "Merchant")], max_length=10)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    facility_name = models.CharField(max_length=255, blank=True)   # buyer: hospital/clinic name
    business_name = models.CharField(max_length=255, blank=True)   # merchant: storefront name
    is_verified_merchant = models.BooleanField(default=False)      # drives the "Verified Supplier" badge, §3.3
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2.2 Endpoints

| Method | Path | Auth | Called by (Kotlin) |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | none | `feature-auth` register screen |
| `POST` | `/api/v1/auth/login` | none | `feature-auth` login screen |
| `POST` | `/api/v1/auth/refresh` | none (refresh token is the credential) | `core-network` auth interceptor, on 401 |
| `POST` | `/api/v1/auth/logout` | JWT | Profile → logout |
| `GET` | `/api/v1/auth/me` | JWT | app launch — resolves role for nav fork (§5) |
| `PATCH` | `/api/v1/auth/me` | JWT | `feature-profile` edit |
| `POST` | `/api/v1/auth/send-phone-otp` | JWT | phone verification, register flow |
| `POST` | `/api/v1/auth/verify-phone` | JWT | phone verification, register flow |
| `POST` | `/api/v1/auth/forgot-password` | none | `feature-auth` forgot-password screen |
| `POST` | `/api/v1/auth/forgot-password/confirm` | none | `feature-auth` forgot-password screen |

**Register — request:**
```json
{
  "role": "buyer",
  "email": "procurement@amanihospital.co.tz",
  "password": "12+ chars",
  "phone": "+255712345678",
  "first_name": "Grace",
  "last_name": "Mushi",
  "facility_name": "Amani Hospital"
}
```
`facility_name` for `role: "buyer"`, `business_name` for `role: "merchant"` — serializer validates the
matching field is present for the chosen role, the other is rejected if sent.

**Login — response `data`:**
```json
{
  "access_token": "...", "refresh_token": "...", "expires_in": 900,
  "role": "buyer", "phone_verified": true, "profile_complete": true
}
```
`expires_in` and the verification flags exist specifically so the client doesn't need a second `GET
/me` round-trip on login — same reasoning SendAfrica's own login response uses.

**Send/verify phone OTP** — same shape and behavior as SendAfrica's own `send-phone-otp`/`verify-phone`
(§7's reference implementation): OTP sent via SMS, 6-digit, 15-minute expiry. Under the hood this app
calls the same `notifications.clients.SendAfricaClient.send_sms()` used for order notifications (§8)
— one SMS-sending code path in the whole backend, not two.

### 2.3 Errors specific to this app

`400 weak_password`, `400 invalid_phone`, `400 invalid_otp`, `401 invalid_credentials`,
`401 invalid_refresh_token`, `403 phone_not_verified` (blocks checkout in `bookings`, not login),
`409 email_exists`.

---

## 3. `addresses`

### 3.1 Model

```python
# apps/addresses/models.py
class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=50)                # "Main receiving", "Pharmacy stores"
    facility_name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=16)
    delivery_notes = models.TextField(blank=True)
    address_type = models.CharField(choices=[("delivery", "Delivery"), ("billing", "Billing"), ("both", "Both")], default="both", max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

Field-for-field match with `AddressEntity` in `KOTLIN.md` §4.9 — this is intentional; the DTO↔domain
mapper on the Kotlin side is a straight rename, no transformation logic needed.

### 3.2 Endpoints

| Method | Path | Auth | Called by |
|---|---|---|---|
| `GET` | `/api/v1/addresses` | JWT (buyer) | `feature-profile` address book, `feature-checkout` address picker |
| `POST` | `/api/v1/addresses` | JWT (buyer) | "Add address" bottom sheet |
| `PUT` | `/api/v1/addresses/{id}` | JWT (buyer, owner) | "Edit" — including edits made mid-checkout (§4.6) |
| `DELETE` | `/api/v1/addresses/{id}` | JWT (buyer, owner) | address book delete |

`services.set_default()` runs inside a transaction that unsets any other `is_default=True` row for the
account — never more than one default at a time. `PUT` with `is_default: true` triggers this
automatically rather than needing a separate endpoint.

---

## 4. `equipment`

### 4.1 Models

```python
# apps/equipment/models.py
class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    merchant = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    category = models.CharField(choices=[
        ("diagnostic", "Diagnostic"), ("rehabilitation", "Rehabilitation"),
        ("life_support", "Life Support"), ("mobility", "Mobility"),
        ("sterilization", "Sterilization"), ("monitoring", "Monitoring"),
    ], max_length=20)
    description = models.TextField()
    specs = models.JSONField(default=dict)          # {"model": "...", "manufacturer": "...", "power": "..."}
    daily_rate_tzs = models.PositiveIntegerField()
    is_featured = models.BooleanField(default=False)  # the SRS's "Featured Listings" revenue stream, §4.3
    is_active = models.BooleanField(default=True)      # soft-delete instead of hard delete
    created_at = models.DateTimeField(auto_now_add=True)

class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    url = models.URLField()                          # MinIO/R2 object URL
    sort_order = models.PositiveSmallIntegerField(default=0)

class AvailabilityBlock(models.Model):
    """A date range the product is NOT available — booked or blacked out by the merchant."""
    id = models.UUIDField(primary_key=True, default=uuid4)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="blocked_ranges")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(choices=[("booked", "Booked"), ("maintenance", "Maintenance")], max_length=15)
    sub_order = models.ForeignKey("bookings.SubOrder", null=True, blank=True, on_delete=models.SET_NULL)
```

### 4.2 Endpoints

| Method | Path | Auth | Called by |
|---|---|---|---|
| `GET` | `/api/v1/products` | none (public browse) | `feature-catalog` grid — `?category=&search=&page=&per_page=` |
| `GET` | `/api/v1/products/{id}` | none | `feature-catalog` product detail |
| `GET` | `/api/v1/products/{id}/availability` | none | rental-period date picker (§4.4) — returns blocked ranges only |
| `GET` | `/api/v1/merchants/{id}` | none | merchant trust card tap-through |
| `POST` | `/api/v1/products` | JWT (merchant) | `feature-merchant` listing create |
| `PUT` | `/api/v1/products/{id}` | JWT (merchant, owner) | `feature-merchant` listing edit |
| `DELETE` | `/api/v1/products/{id}` | JWT (merchant, owner) | soft-deletes (`is_active=False`), never hard-deletes a product with order history |
| `GET` | `/api/v1/merchants/me/products` | JWT (merchant) | `feature-merchant` listing management list |

**`GET /api/v1/products/{id}/availability` — response `data`:**
```json
{ "blocked_ranges": [{ "start_date": "2026-08-01", "end_date": "2026-08-05" }] }
```
Kotlin greys these out in the date-range picker (§4.4); the actual conflict check still happens
server-side in `equipment.services.check_availability()` at cart-add and again at checkout — never
trust a client-computed "this range looks free."

---

## 5. `cart`

Purely a sync mirror of the Kotlin Room cart in `KOTLIN.md` §6.1 — this app has no independent UI, no
business logic beyond "does this line still resolve to a real, available, correctly-priced product."

### 5.1 Models

```python
# apps/cart/models.py
class Cart(models.Model):
    account = models.OneToOneField("accounts.Account", on_delete=models.CASCADE, primary_key=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartLine(models.Model):
    id = models.UUIDField(primary_key=True)          # same client-generated UUID as CartLineEntity.id
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("equipment.Product", on_delete=models.CASCADE)
    rental_start = models.DateField()
    rental_end = models.DateField()
    quantity = models.PositiveSmallIntegerField(default=1)
    added_at = models.DateTimeField()
```

### 5.2 Endpoints

| Method | Path | Auth | Called by |
|---|---|---|---|
| `GET` | `/api/v1/cart` | JWT (buyer) | cross-device cart restore on login |
| `PATCH` | `/api/v1/cart` | JWT (buyer) | debounced full-cart sync from `CartRepository` (§6.1) |

`PATCH` takes the **entire current line list** and replaces server state (`Idempotency-Key:
{cart_id}-{last_mutation_id}`, matching the pattern `KOTLIN.md` already specifies) — no line-level
`POST`/`DELETE` sub-endpoints, because the client already resolves add/edit/remove locally in Room and
only needs the server to end up matching, not to replay each mutation individually. `services.
replace_cart()` re-validates every line's price and availability against `equipment` on every sync and
flags any line that's gone stale (price changed, now unavailable) in the response so the Cart screen
can surface it before checkout, rather than discovering it at payment time.

---

## 6. `bookings`

### 6.1 Models

```python
# apps/bookings/models.py
class OrderGroup(models.Model):
    """The buyer-facing container. Splits into one SubOrder per merchant."""
    id = models.UUIDField(primary_key=True, default=uuid4)
    buyer = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="order_groups")
    delivery_address = models.ForeignKey("addresses.Address", on_delete=models.PROTECT, related_name="+")
    billing_address = models.ForeignKey("addresses.Address", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

class SubOrder(models.Model):
    """One per merchant per checkout — the unit everything else (payment, contract, fulfillment) hangs off."""
    id = models.UUIDField(primary_key=True, default=uuid4)
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name="sub_orders")
    merchant = models.ForeignKey("accounts.Account", on_delete=models.PROTECT, related_name="incoming_orders")
    status = models.CharField(choices=[
        ("pending_payment", "Pending Payment"), ("confirmed", "Confirmed"),
        ("dispatched", "Dispatched"), ("delivered", "Delivered"),
        ("return_due", "Return Due"), ("returned", "Returned"),
        ("cancelled", "Cancelled"), ("payment_failed", "Payment Failed"),
    ], default="pending_payment", max_length=20)
    special_instructions = models.TextField(blank=True)
    subtotal_tzs = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class SubOrderLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("equipment.Product", on_delete=models.PROTECT)
    product_name_snapshot = models.CharField(max_length=255)   # frozen at order time — product may change later
    daily_rate_snapshot_tzs = models.PositiveIntegerField()
    rental_start = models.DateField()
    rental_end = models.DateField()
    quantity = models.PositiveSmallIntegerField()
    line_total_tzs = models.PositiveIntegerField()
```

### 6.2 Endpoints

| Method | Path | Auth | Called by |
|---|---|---|---|
| `POST` | `/api/v1/checkout` | JWT (buyer, `phone_verified=True`) | §4.6 step 1 → 2 transition |
| `GET` | `/api/v1/orders` | JWT | buyer: their orders; merchant: incoming orders — `?status=` filters the tabs in §4.7/§4.10 |
| `GET` | `/api/v1/orders/{sub_order_id}` | JWT (buyer owner or merchant owner) | order detail, §4.7 |
| `PATCH` | `/api/v1/orders/{sub_order_id}/status` | JWT (merchant, owner) | accept/reject/dispatch/deliver/mark-returned, §4.10 |

**`POST /api/v1/checkout` — request:**
```json
{ "delivery_address_id": "...", "billing_address_id": "...", "notes": "Deliver to loading dock" }
```
(Reads the buyer's server-side cart — no line items in the request body; `cart.services` is the source
of truth for what's being purchased, closing the gap where a client could checkout with different
items than what the server thinks is in the cart.)

**Response `data`:**
```json
{
  "order_group_id": "...",
  "sub_orders": [
    { "id": "...", "merchant_name": "TIBA Medical Supplies", "subtotal_tzs": 240000, "status": "pending_payment" }
  ]
}
```
Client immediately calls `POST /api/v1/orders/{sub_order_id}/pay` (payments app, §7) for each
`sub_order_id` returned here — the checkout call and the payment call are deliberately separate, so a
buyer with three merchants in cart pays each sub-order's USSD push independently and can retry one
without touching the others.

`services.checkout()` is a single DB transaction: validates every cart line again (price + availability
— same re-check `cart.services.replace_cart()` does, run once more here since time has passed since the
last cart sync), locks the `AvailabilityBlock` rows it's about to create, groups lines by
`product.merchant_id`, creates one `SubOrder` + its `SubOrderLine`s per merchant, clears the cart. If
any line fails validation, the whole transaction rolls back and the response is a `409
cart_changed` error naming which line — never a partial checkout.

---

## 7. `payments`

Full detail already specified in `KOTLIN.md` §8 — reproduced here only as the endpoint/model summary
so this document is self-contained; §8 remains the canonical source for the webhook signature code.

### 7.1 Models

```python
# apps/payments/models.py
class PaymentIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    sub_order = models.OneToOneField("bookings.SubOrder", on_delete=models.CASCADE, related_name="payment")
    snippe_reference = models.CharField(max_length=64, unique=True)
    status = models.CharField(choices=[
        ("pending", "Pending"), ("completed", "Completed"),
        ("failed", "Failed"), ("expired", "Expired"),
    ], default="pending", max_length=15)
    amount_tzs = models.PositiveIntegerField()
    network = models.CharField(max_length=20, blank=True)   # "mpesa" / "airtel" / "mixx" / "halotel"
    failure_reason = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

class WebhookEvent(models.Model):
    """Dedup table — Snippe's own docs say the same event may arrive more than once."""
    id = models.UUIDField(primary_key=True, default=uuid4)
    provider = models.CharField(max_length=20)   # "snippe"
    event_id = models.CharField(max_length=64)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["provider", "event_id"]
```

### 7.2 Endpoints

| Method | Path | Auth | Called by |
|---|---|---|---|
| `POST` | `/api/v1/orders/{sub_order_id}/pay` | JWT (buyer, owner) | §4.6 step 2 — creates the Snippe payment intent, exact match to `PaymentApi.initiatePayment` in `KOTLIN.md` §8.4 |
| `GET` | `/api/v1/orders/{sub_order_id}/payment-status` | JWT (buyer, owner) | poll-as-fallback, exact match to `PaymentApi.paymentStatus` |
| `POST` | `/webhooks/snippe` | Snippe signature only (not JWT, not under `/api/v1`) | Snippe's servers — never called by the Kotlin app |

`clients.SnippeClient` is the **only** file in the whole codebase that holds `SNIPPE_API_KEY`. Every
other app that needs a payment reaches `payments.services`, never `clients` directly.

---

## 8. `contracts`

### 8.1 Models

```python
# apps/contracts/models.py
class Contract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    sub_order = models.OneToOneField("bookings.SubOrder", on_delete=models.CASCADE, related_name="contract")
    pdf_url = models.URLField()                       # MinIO/R2, generated once, immutable after signing
    generated_at = models.DateTimeField(auto_now_add=True)

class Signature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="signatures")
    signer = models.ForeignKey("accounts.Account", on_delete=models.PROTECT)
    signature_image_url = models.URLField()            # PNG from the Canvas signature pad, §4.6 step 3
    signed_at = models.DateTimeField(auto_now_add=True)
```

### 8.2 Endpoints

| Method | Path | Auth | Called by |
|---|---|---|---|
| `GET` | `/api/v1/orders/{sub_order_id}/contract` | JWT (buyer or merchant, party to the order) | §4.6 step 3 preview, §4.7 order detail download |
| `POST` | `/api/v1/orders/{sub_order_id}/contract/sign` | JWT (buyer, owner) | §4.6 step 3 signature pad submit |

`services.generate_contract_pdf()` fires automatically once a `SubOrder` hits `confirmed` (triggered
from `payments.services` on a successful webhook, §7) — there's no manual "generate contract" endpoint
because the client never needs to ask for one to exist, only to view or sign it. Signing marks the
`SubOrder` eligible to move to `dispatched` — merchants can't dispatch equipment against an unsigned
contract.

---

## 9. `notifications`

Boundary already established in `KOTLIN.md` §7 — MES owns this table end to end; it never proxies
SendAfrica's own dashboard notifications.

### 9.1 Models

```python
# apps/notifications/models.py
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(choices=[
        ("order_confirmed", "Order Confirmed"), ("payment_received", "Payment Received"),
        ("return_due", "Return Due"), ("merchant_message", "Merchant Message"),
    ], max_length=20)
    title = models.CharField(max_length=255)
    body = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DeviceToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE, related_name="device_tokens")
    fcm_token = models.CharField(max_length=255, unique=True)
    registered_at = models.DateTimeField(auto_now_add=True)
```

### 9.2 Endpoints

| Method | Path | Auth | Called by (exact match to `NotificationApi` in `KOTLIN.md` §7.3) |
|---|---|---|---|
| `GET` | `/api/v1/notifications` | JWT | `NotificationApi.list` |
| `GET` | `/api/v1/notifications/unread-count` | JWT | badge poll on bell icon and bottom nav |
| `PATCH` | `/api/v1/notifications/{id}/read` | JWT (owner) | `NotificationApi.markRead` |
| `POST` | `/api/v1/notifications/read-all` | JWT | "mark all read" |
| `POST` | `/api/v1/notifications/register-device` | JWT | app launch, registers the FCM token |

`services.notify(event, account, context)` is the single fan-out function every other app's
`services.py` calls on a domain event (order confirmed, payment received, return due tomorrow — the
Celery-beat job that scans `SubOrderLine.rental_end` for "due tomorrow" is what triggers that last one).
It writes the `Notification` row, sends FCM via the registered `DeviceToken`s, and — only for the event
types listed in `KOTLIN.md` §7.1 — calls `clients.SendAfricaClient.send_sms()`. This is the **only**
file that holds `SENDAFRICA_API_KEY`.

---

## 10. Full Endpoint Index

Every route the Kotlin app touches, in one place, for a build-order checklist:

```
POST    /api/v1/auth/register
POST    /api/v1/auth/login
POST    /api/v1/auth/refresh
POST    /api/v1/auth/logout
GET     /api/v1/auth/me
PATCH   /api/v1/auth/me
POST    /api/v1/auth/send-phone-otp
POST    /api/v1/auth/verify-phone
POST    /api/v1/auth/forgot-password
POST    /api/v1/auth/forgot-password/confirm

GET     /api/v1/addresses
POST    /api/v1/addresses
PUT     /api/v1/addresses/{id}
DELETE  /api/v1/addresses/{id}

GET     /api/v1/products
GET     /api/v1/products/{id}
GET     /api/v1/products/{id}/availability
GET     /api/v1/merchants/{id}
GET     /api/v1/merchants/me/products
POST    /api/v1/products
PUT     /api/v1/products/{id}
DELETE  /api/v1/products/{id}

GET     /api/v1/cart
PATCH   /api/v1/cart

POST    /api/v1/checkout
GET     /api/v1/orders
GET     /api/v1/orders/{sub_order_id}
PATCH   /api/v1/orders/{sub_order_id}/status

POST    /api/v1/orders/{sub_order_id}/pay
GET     /api/v1/orders/{sub_order_id}/payment-status
POST    /webhooks/snippe                              ← Snippe → Django, not client-facing

GET     /api/v1/orders/{sub_order_id}/contract
POST    /api/v1/orders/{sub_order_id}/contract/sign

GET     /api/v1/notifications
GET     /api/v1/notifications/unread-count
PATCH   /api/v1/notifications/{id}/read
POST    /api/v1/notifications/read-all
POST    /api/v1/notifications/register-device
```

30 endpoints total, across 8 domain apps. Every one traces back to a screen or repository call in
`KOTLIN.md`.

---

## 11. Settings & Environment

```python
# config/settings/base.py — the only secrets this backend needs
SNIPPE_API_KEY = env("SNIPPE_API_KEY")
SNIPPE_WEBHOOK_SECRET = env("SNIPPE_WEBHOOK_SECRET")
SNIPPE_WEBHOOK_URL = env("SNIPPE_WEBHOOK_URL")            # e.g. https://api.mes.co.tz/webhooks/snippe

SENDAFRICA_API_KEY = env("SENDAFRICA_API_KEY")

FIREBASE_CREDENTIALS_JSON = env("FIREBASE_CREDENTIALS_JSON")

DATABASE_URL = env("DATABASE_URL")                        # PostgreSQL
REDIS_URL = env("REDIS_URL")                               # Celery broker + result backend
MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY = env(...)  # or R2 equivalents

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),         # matches SendAfrica's own convention, §7
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.mes_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.MesPagination",
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
}
```

`requirements.txt` core set: `django`, `djangorestframework`, `djangorestframework-simplejwt`,
`psycopg2-binary`, `celery`, `redis`, `django-storages` (MinIO/R2), `requests` (Snippe + SendAfrica
clients — no SDK needed for either, both are plain JSON-over-HTTPS), `reportlab` or `weasyprint`
(contract PDF generation), `django-cors-headers` (the Kotlin app is a native client, not a browser, so
CORS is mostly moot — kept only for any web-based merchant dashboard that might reuse this same API
later, per `KOTLIN.md`'s "not in scope" list — this is the one line in the whole spec that's future-
proofing rather than a current Kotlin need, and it's a `pip install`, not an endpoint, so it doesn't
violate §0.1).

---

## 12. Build Order

Matches `KOTLIN.md` §10's phased plan, backend side runs one phase ahead of the client phase it
unblocks:

| Phase | Backend work | Unblocks Kotlin phase |
|---|---|---|
| 0 | `core` app (envelope, pagination, exceptions, permissions) + project scaffold | — |
| 1 | `accounts` + `addresses` | Kotlin phase 1–2 (auth, onboarding) |
| 2 | `equipment` (read endpoints first, merchant CRUD after) | Kotlin phase 3 (catalog) |
| 3 | `cart` | Kotlin phase 4 (cart) |
| 4 | `bookings` (checkout + sub-order split) | Kotlin phase 5 (checkout, address/order half) |
| 5 | `payments` (Snippe integration + webhook) | Kotlin phase 5 (checkout, payment half) — **this is the phase that needs a real Snippe test key before either side can finish** |
| 6 | `contracts` | Kotlin phase 5 (checkout, contract half) |
| 7 | `notifications` (in-app + FCM + SendAfrica SMS) | Kotlin phase 7 |
| 8 | Merchant-side endpoints already exist from phases 2/4 by this point — no new backend phase, just Kotlin catching up | Kotlin phase 8 (merchant UI) |
