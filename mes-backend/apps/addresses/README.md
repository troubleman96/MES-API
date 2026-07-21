# apps/addresses/ — Address Management

Manages delivery and billing addresses for buyers. Addresses are used during checkout to determine where equipment is delivered and where invoices are sent.

---

## File Inventory

### `apps/addresses/__init__.py` (1 line)

Sets default app config to `AddressesConfig`.

### `apps/addresses/apps.py` (7 lines)

**Class:** `AddressesConfig(AppConfig)`
- `name = "apps.addresses"`
- `verbose_name = "Addresses"`

### `apps/addresses/models.py` (29 lines)

**Class:** `Address(models.Model)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `account` | ForeignKey(Account) | CASCADE, `related_name="addresses"` | Owner of the address |
| `label` | CharField(50) | Required | Short label (e.g., "Main Clinic", "Warehouse") |
| `facility_name` | CharField(255) | Required | Hospital or facility name |
| `address_line1` | CharField(255) | Required | Street address |
| `address_line2` | CharField(255) | Blank | Additional address info |
| `ward` | CharField(100) | Blank | Ward/subdivision |
| `district` | CharField(100) | Blank | District |
| `city` | CharField(100) | Required | City name |
| `contact_name` | CharField(100) | Required | Person to contact at delivery |
| `contact_phone` | CharField(16) | Required | Contact phone number |
| `delivery_notes` | TextField | Blank | Special delivery instructions |
| `address_type` | CharField(10) | Choices: `delivery`, `billing`, `both` | Default: `both` |
| `is_default` | BooleanField | Default: False | Whether this is the default address |
| `created_at` | DateTimeField | Auto | Creation timestamp |

**Meta:** `db_table = "addresses"`, `ordering = ["-is_default", "-created_at"]`

### `apps/addresses/serializers.py` (14 lines)

**Class:** `AddressSerializer(serializers.ModelSerializer)`

Fields: `id`, `label`, `facility_name`, `address_line1`, `address_line2`, `ward`, `district`, `city`, `contact_name`, `contact_phone`, `delivery_notes`, `address_type`, `is_default`, `created_at`

Read-only: `id`, `created_at`

### `apps/addresses/views.py` (26 lines)

| View | HTTP Method | Auth Required | Role | Description |
|------|------------|---------------|------|-------------|
| `AddressListView` | GET | Yes | Buyer | List all addresses |
| `AddressListView` | POST | Yes | Buyer | Create new address |
| `AddressDetailView` | PUT | Yes | Buyer | Update address |
| `AddressDetailView` | DELETE | Yes | Buyer | Delete address |

### `apps/addresses/urls.py` (8 lines)

URL patterns under `/api/v1/addresses/`:

| URL Pattern | View | Name |
|------------|------|------|
| `""` | `AddressListView` | `address_list` |
| `<uuid:pk>/` | `AddressDetailView` | `address_detail` |

### `apps/addresses/services.py` (67 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `list_addresses()` | `user` | Returns all addresses for the authenticated buyer |
| `create_address()` | `user`, `data` | Creates address; if `is_default=True`, unsets other defaults |
| `update_address()` | `user`, `address_id`, `data` | Partial update; handles default flag. 404 if not found. |
| `delete_address()` | `user`, `address_id` | Deletes address. 404 if not found. Returns 204. |
| `set_default()` | `user`, `address_id` | Atomically sets one address as default, unsets others |
| `_unset_other_defaults()` | `user`, `exclude_id` | Internal helper to clear default flag on other addresses |

---

## How This Directory Connects to the App

- **Checkout dependency** — The `bookings/services.py:checkout()` function requires valid `delivery_address_id` and `billing_address_id` to create an order.
- **OrderGroup model** stores references to both delivery and billing addresses (with `PROTECT` on delete to prevent address deletion while orders exist).
- **Buyer-only access** — All endpoints require `IsBuyer` permission, ensuring only buyers can manage addresses.
- **Default address logic** — When creating or updating an address with `is_default=True`, the service automatically unsets the default flag on all other addresses for that user.
