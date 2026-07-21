# apps/cart/ — Shopping Cart

Manages the buyer's shopping cart: adding items, validating availability, syncing cart state, and preparing for checkout.

---

## File Inventory

### `apps/cart/__init__.py` (1 line)

Sets default app config to `CartConfig`.

### `apps/cart/apps.py` (7 lines)

**Class:** `CartConfig(AppConfig)`
- `name = "apps.cart"`
- `verbose_name = "Cart"`

### `apps/cart/models.py` (24 lines)

#### `Cart(models.Model)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `account` | OneToOneField(Account) | CASCADE, Primary key | One cart per user |
| `updated_at` | DateTimeField | Auto (auto_now) | Last modification time |

**Meta:** `db_table = "carts"`

#### `CartLine(models.Model)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `cart` | ForeignKey(Cart) | CASCADE, `related_name="lines"` | Parent cart |
| `product` | ForeignKey(Product) | CASCADE | Equipment item |
| `rental_start` | DateField | Required | Rental start date |
| `rental_end` | DateField | Required | Rental end date |
| `quantity` | PositiveSmallIntegerField | Default: 1 | Number of units |
| `added_at` | DateTimeField | Required | When item was added |

**Meta:** `db_table = "cart_lines"`

### `apps/cart/serializers.py` (28 lines)

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `CartLineSerializer` | `id`, `product`, `product_name` (read-only), `daily_rate_tzs` (read-only), `rental_start`, `rental_end`, `quantity`, `added_at` | Individual cart item |
| `CartSerializer` | `account` (read-only), `lines` (nested), `updated_at` (read-only) | Full cart with items |
| `CartSyncSerializer` | `lines` (list of CartLineSerializer) | Input for cart replacement |

### `apps/cart/views.py` (18 lines)

| View | HTTP Method | Auth Required | Role | Description |
|------|------------|---------------|------|-------------|
| `CartView` | GET | Yes | Buyer | Get current cart |
| `CartView` | PATCH | Yes | Buyer | Replace entire cart contents |

### `apps/cart/urls.py` (7 lines)

URL pattern under `/api/v1/cart/`:

| URL Pattern | View | Name |
|------------|------|------|
| `""` | `CartView` | `cart` |

### `apps/cart/services.py` (107 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `get_cart()` | `user` | Gets or creates cart, returns serialized data |
| `replace_cart()` | `user`, `lines_data` | Atomic: deletes all lines, recreates from input. Validates each line. |
| `validate_cart_for_checkout()` | `user` | Validates cart is non-empty, all products active, no conflicts |

**Cart replacement validation per line:**

| Check | Stale Reason | Description |
|-------|-------------|-------------|
| Product exists and active | `product_not_found` | Product may have been deleted |
| `rental_start < rental_end` | `invalid_dates` | Date range must be positive |
| No availability conflict | `unavailable` | Product already booked for those dates |
| Price matches current | `price_changed` | Product price changed since added |

**Stale lines** are returned in the response so the mobile app can inform the user which items couldn't be added and why.

**Response format:**
```json
{
  "success": true,
  "data": {
    "cart": { "lines": [...], "updated_at": "..." },
    "stale_lines": [
      { "product": "uuid", "reason": "unavailable", "product_name": "..." }
    ]
  }
}
```

---

## How This Directory Connects to the App

- **Pre-checkout staging** — The cart is the staging area where buyers assemble rental items before checkout.
- **Cart replacement pattern** — Instead of individual add/remove endpoints, the API uses a "replace entire cart" pattern (PATCH). The mobile app sends the full desired cart state; the server diffs and validates.
- **Checkout dependency** — `bookings/services.py:checkout()` reads cart lines to create orders, then deletes the cart lines after successful checkout.
- **Availability checking** — Cart validation checks `AvailabilityBlock` to prevent adding items that are already booked for overlapping dates.
- **Price validation** — Cart sync checks current product prices to ensure the buyer sees up-to-date pricing.
- **Buyer-only access** — All cart endpoints require `IsBuyer` permission.
