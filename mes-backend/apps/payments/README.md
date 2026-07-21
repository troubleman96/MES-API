# apps/payments/ — Payment Processing

Handles payment initiation via the Snippe mobile money gateway, webhook processing for payment status updates, and payment intent tracking.

---

## File Inventory

### `apps/payments/__init__.py` (1 line)

Sets default app config to `PaymentsConfig`.

### `apps/payments/apps.py` (7 lines)

**Class:** `PaymentsConfig(AppConfig)`
- `name = "apps.payments"`
- `verbose_name = "Payments"`

### `apps/payments/models.py` (36 lines)

#### `PaymentIntent(models.Model)`

Tracks a payment attempt for a sub-order.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `sub_order` | OneToOneField(SubOrder) | CASCADE, `related_name="payment"` | Associated order |
| `snippe_reference` | CharField(64) | Unique | Snippe payment reference ID |
| `status` | CharField(15) | Choices: `pending`, `completed`, `failed`, `expired` | Payment status |
| `amount_tzs` | PositiveIntegerField | Required | Amount in Tanzanian Shillings |
| `network` | CharField(255) | Blank | Mobile money network (e.g., "Vodacom", "Tigo") |
| `failure_reason` | CharField(255) | Blank | Reason for failure |
| `expires_at` | DateTimeField | Required | Payment expiration (4 hours from creation) |
| `created_at` | DateTimeField | Auto | Creation timestamp |

**Meta:** `db_table = "payment_intents"`

#### `WebhookEvent(models.Model)`

Idempotency tracker for webhook events.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `provider` | CharField(20) | Required | Payment provider (e.g., "snippe") |
| `event_id` | CharField(64) | Required | Provider's event identifier |
| `received_at` | DateTimeField | Auto | When the event was received |

**Meta:** `db_table = "webhook_events"`, `unique_together = ["provider", "event_id"]`

### `apps/payments/serializers.py` (18 lines)

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `PaymentIntentSerializer` | All PaymentIntent fields | Payment data output |
| `WebhookEventSerializer` | `id`, `provider`, `event_id`, `received_at` | Webhook event data |

### `apps/payments/views.py` (18 lines)

| View | HTTP Method | Auth Required | Role | Description |
|------|------------|---------------|------|-------------|
| `PayView` | POST | Yes | Buyer | Initiate payment for a sub-order |
| `PaymentStatusView` | GET | Yes | Buyer/Merchant | Check payment status |

### `apps/payments/urls.py` (8 lines)

URL patterns under `/api/v1/orders/`:

| URL Pattern | View | Name |
|------------|------|------|
| `<uuid:pk>/pay/` | `PayView` | `pay` |
| `<uuid:pk>/payment-status/` | `PaymentStatusView` | `payment_status` |

### `apps/payments/webhook_urls.py` (7 lines)

URL pattern under `/webhooks/`:

| URL Pattern | View | Name |
|------------|------|------|
| `snippe/` | `snippe_webhook` | `snippe_webhook` |

### `apps/payments/clients.py` (62 lines)

HTTP client for the Snippe payment gateway.

**Class:** `SnippeClient`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `__init__()` | — | Reads `SNIPPE_API_KEY` from Django settings |
| `initiate_payment()` | `amount_tzs`, `phone`, `first_name`, `last_name`, `email`, `description` | POSTs to `https://api.snippe.sh/v1/payments` with payment details. Returns response data dict. |
| `verify_webhook_signature()` | `payload_body`, `timestamp`, `signature_header` | Computes HMAC-SHA256 of `"{timestamp}.{body}"` using webhook secret. Uses `hmac.compare_digest` for timing-safe comparison. |

**Request format:**
```json
{
  "payment_type": "mobile",
  "amount": 50000,
  "currency": "TZS",
  "phone_number": "0694157749",
  "first_name": "Juma",
  "last_name": "Kitonda",
  "email": "juma.kitonda@mes.co.tz",
  "description": "MES Order add83f5d",
  "webhook_url": "https://api.mes.co.tz/webhooks/snippe"
}
```

### `apps/payments/webhooks.py` (34 lines)

Django view (function-based) for receiving Snippe webhook callbacks.

**Function:** `snippe_webhook(request)` — `@csrf_exempt @require_POST`

**Flow:**
1. Extract `X-Webhook-Timestamp` and `X-Webhook-Signature` headers
2. Verify HMAC-SHA256 signature using `SnippeClient.verify_webhook_signature()`
3. Parse JSON body
4. Extract `event_id` from payload
5. Call `services.handle_webhook(event_id, payload)`
6. Return 200 on success, 401 on bad signature, 400 on bad JSON

### `apps/payments/services.py` (117 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `create_payment()` | `user`, `sub_order_id` | Initiates Snippe payment (idempotent: returns existing pending intent) |
| `get_payment_status()` | `user`, `sub_order_id` | Returns latest payment intent |
| `handle_webhook()` | `event_id`, `payload` | Processes webhook events (idempotent) |

**Payment initiation flow:**
1. Verify sub-order exists, user is the buyer, status is `pending_payment`
2. Check for existing pending PaymentIntent (idempotent return)
3. Call `SnippeClient.initiate_payment()` with order details
4. Create PaymentIntent with reference, amount, expiry (+4 hours)
5. Return 201

**Webhook event handling:**

| Event Type | PaymentIntent Action | SubOrder Action | Additional |
|-----------|---------------------|----------------|------------|
| `payment.completed` | Status → `completed` | Status → `confirmed` | Generate contract PDF |
| `payment.failed` | Status → `failed` + `failure_reason` | Status → `payment_failed` | — |
| `payment.expired` | Status → `expired` | Status → `payment_failed` | — |

**Idempotency:** Events are tracked in `WebhookEvent` model. Duplicate events are silently ignored.

---

## How This Directory Connects to the App

- **Order lifecycle trigger** — Successful payment transitions orders from `pending_payment` to `confirmed`, enabling the merchant to proceed with dispatch.
- **Contract generation** — Upon `payment.completed`, the webhook handler automatically triggers `contracts.services.generate_contract_pdf()` to create the rental agreement.
- **Webhook security** — HMAC-SHA256 signature verification ensures webhooks are genuinely from Snippe, preventing spoofed payment confirmations.
- **External dependency** — The Snippe gateway is the primary payment method (USSD mobile money). All payment flows go through their REST API.
- **Idempotent design** — Both payment initiation and webhook processing are idempotent, preventing duplicate charges or order confirmations from network retries.
