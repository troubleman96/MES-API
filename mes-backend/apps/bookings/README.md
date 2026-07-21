# apps/bookings/ — Order Management

Handles the full order lifecycle: checkout (converting cart to orders), order listing, order details, and the state machine for order status transitions.

---

## File Inventory

### `apps/bookings/__init__.py` (1 line)

Sets default app config to `BookingsConfig`.

### `apps/bookings/apps.py` (7 lines)

**Class:** `BookingsConfig(AppConfig)`
- `name = "apps.bookings"`
- `verbose_name = "Bookings"`

### `apps/bookings/models.py` (55 lines)

Three models that represent the order hierarchy.

#### `OrderGroup(models.Model)`

A single checkout transaction that may contain items from multiple merchants.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `buyer` | ForeignKey(Account) | CASCADE, `related_name="order_groups"` | The buyer who placed the order |
| `delivery_address` | ForeignKey(Address) | PROTECT | Where equipment will be delivered |
| `billing_address` | ForeignKey(Address) | PROTECT | Billing address |
| `created_at` | DateTimeField | Auto | Order creation timestamp |

**Meta:** `db_table = "order_groups"`, `ordering = ["-created_at"]`

#### `SubOrder(models.Model)`

One merchant's portion of an order group. Each merchant gets their own sub-order.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `order_group` | ForeignKey(OrderGroup) | CASCADE, `related_name="sub_orders"` | Parent order group |
| `merchant` | ForeignKey(Account) | PROTECT, `related_name="incoming_orders"` | The merchant fulfilling this sub-order |
| `status` | CharField(20) | Choices (see below) | Current status |
| `special_instructions` | TextField | Blank | Buyer's notes for this merchant |
| `subtotal_tzs` | PositiveIntegerField | Required | Total cost for this sub-order |
| `created_at` | DateTimeField | Auto | Creation timestamp |

**Status choices:**
| Status | Description |
|--------|-------------|
| `pending_payment` | Awaiting payment (initial) |
| `confirmed` | Payment received, order confirmed |
| `dispatched` | Equipment shipped/picked up |
| `delivered` | Equipment delivered to buyer |
| `return_due` | Equipment due for return |
| `returned` | Equipment returned to merchant |
| `cancelled` | Order cancelled |
| `payment_failed` | Payment failed or expired |

**Meta:** `db_table = "sub_orders"`, `ordering = ["-created_at"]`

#### `SubOrderLine(models.Model)`

Individual line items within a sub-order.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `sub_order` | ForeignKey(SubOrder) | CASCADE, `related_name="lines"` | Parent sub-order |
| `product` | ForeignKey(Product) | PROTECT | Rented product |
| `product_name_snapshot` | CharField(255) | Required | Product name at time of order |
| `daily_rate_snapshot_tzs` | PositiveIntegerField | Required | Price at time of order |
| `rental_start` | DateField | Required | Rental start date |
| `rental_end` | DateField | Required | Rental end date |
| `quantity` | PositiveSmallIntegerField | Required | Number of units |
| `line_total_tzs` | PositiveIntegerField | Required | Total for this line (rate × days × qty) |

**Meta:** `db_table = "sub_order_lines"`

### `apps/bookings/serializers.py` (50 lines)

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `SubOrderLineSerializer` | All line fields | Detailed line item data |
| `SubOrderSerializer` | All sub-order fields + nested `lines` + `merchant_name` | Full sub-order detail |
| `SubOrderListSerializer` | `id`, `merchant_name`, `subtotal_tzs`, `status`, `created_at` | Summary for order lists |
| `OrderGroupSerializer` | `id`, `buyer`, `delivery_address`, `billing_address`, nested `sub_orders` | Full order group |
| `CheckoutSerializer` | `delivery_address_id`, `billing_address_id`, `notes` | Checkout input |
| `SubOrderStatusSerializer` | `status` (ChoiceField) | Status update input |

### `apps/bookings/views.py` (39 lines)

| View | HTTP Method | Auth Required | Role | Description |
|------|------------|---------------|------|-------------|
| `CheckoutView` | POST | Yes | Buyer | Convert cart to order |
| `OrderListView` | GET | Yes | Buyer/Merchant | List orders |
| `OrderDetailView` | GET | Yes | Buyer/Merchant | View order detail |
| `OrderStatusUpdateView` | PATCH | Yes | Merchant | Update order status |

### `apps/bookings/urls.py` (10 lines)

URL patterns under `/api/v1/`:

| URL Pattern | View | Name |
|------------|------|------|
| `checkout/` | `CheckoutView` | `checkout` |
| `orders/` | `OrderListView` | `order_list` |
| `orders/<uuid:pk>/` | `OrderDetailView` | `order_detail` |
| `orders/<uuid:pk>/status/` | `OrderStatusUpdateView` | `order_status` |

### `apps/bookings/services.py` (177 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `checkout()` | `user`, `data` | Full checkout flow (see below) |
| `list_orders()` | `user`, `query_params` | Lists SubOrders with role-based filtering |
| `get_order()` | `user`, `sub_order_id` | Returns SubOrder detail with ownership check |
| `update_order_status()` | `user`, `sub_order_id`, `new_status` | State machine transition |

**Checkout flow:**
1. Verify phone is verified (403 if not)
2. Validate delivery and billing addresses exist and belong to user
3. Validate cart is non-empty, all products active, no availability conflicts (with `select_for_update` row locking)
4. Create `OrderGroup`
5. Group cart lines by merchant
6. For each merchant group: create `SubOrder` + `SubOrderLine` records with price/name snapshots
7. Create `AvailabilityBlock` for each line item
8. Delete cart lines
9. Return order summary

**Status state machine:**

```
pending_payment → confirmed → dispatched → delivered → return_due → returned
                   ↓
                 cancelled
```

**Dispatch guard:** Cannot transition to `dispatched` without a signed contract (checks both `Contract` and `Signature` models).

---

## How This Directory Connects to the App

- **Checkout is the bridge** — Converts cart items into persistent orders. This is where `CartLine` becomes `SubOrderLine`.
- **Order status drives the workflow** — The state machine controls the entire rental lifecycle from payment to return.
- **Contract dependency** — Dispatching requires a signed contract (`contracts` app), ensuring legal agreements are in place before equipment leaves the merchant.
- **Availability blocking** — Checkout creates `AvailabilityBlock` records in the `equipment` app, preventing double-booking.
- **Role-based views** — Buyers see their orders; merchants see incoming orders. Both views use the same endpoint with different query filters.
- **Payment trigger** — After checkout, the order status is `pending_payment`. The `payments` app transitions it to `confirmed` upon successful payment.
