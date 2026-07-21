# apps/core/ — Shared Framework

The foundation layer used by every other app in the project. Provides standardized response formatting, exception handling, pagination, permissions, and database seeding.

---

## File Inventory

### `apps/__init__.py` (1 line)

Sets the default app config to `apps.core.apps.CoreConfig`.

### `apps/core/__init__.py` (7 lines)

Django AppConfig for the core module.

**Class:** `CoreConfig(AppConfig)`
- `name = "apps.core"`
- `verbose_name = "Core"`
- `default_auto_field = BigAutoField`

### `apps/core/responses.py` (12 lines)

Standardized response helpers that enforce the API envelope format used by every endpoint.

**Functions:**

| Function | Parameters | Returns |
|----------|-----------|---------|
| `envelope_ok()` | `data=None`, `meta=None`, `status=200` | `{"success": true, "data": ..., "error": null, "meta": ...}` |
| `envelope_error()` | `code`, `message`, `status=400` | `{"success": false, "data": null, "error": {"code": ..., "message": ...}, "meta": null}` |

**Usage example:**
```python
from apps.core.responses import envelope_ok, envelope_error

# Success
return envelope_ok(data={"id": "123"}, status=201)

# Error
return envelope_error("not_found", "Product not found.", status=404)
```

### `apps/core/exceptions.py` (12 lines)

Custom DRF exception handler that wraps all exceptions into the envelope format.

**Function:** `mes_exception_handler(exc, context)`
- Catches all DRF exceptions (400, 401, 403, 404, 405, etc.)
- Wraps them into `{"success": false, "error": {"code": ..., "message": ...}}`
- Unhandled exceptions return 500 with generic error message
- Wired into `REST_FRAMEWORK["EXCEPTION_HANDLER"]` in settings

### `apps/core/pagination.py` (19 lines)

Custom pagination class for list endpoints.

**Class:** `MesPagination(PageNumberPagination)`
- `page_size = 25` (default items per page)
- `max_page_size = 200` (client can request up to 200)
- Query parameter: `?per_page=50`
- Wraps paginated results in the envelope format with `items`, `count`, and `meta`

**Response format:**
```json
{
  "success": true,
  "data": {
    "items": [...],
    "count": 150,
    "meta": { "page": 1, "per_page": 25, "total_pages": 6 }
  }
}
```

### `apps/core/permissions.py` (16 lines)

Role-based permission classes for DRF views.

| Permission Class | Logic | Used By |
|-----------------|-------|---------|
| `IsBuyer` | `request.user.role == "buyer"` | Cart, addresses, checkout, order list |
| `IsMerchant` | `request.user.role == "merchant"` | Product CRUD, order status updates |
| `IsOwnerMerchant` | `obj.merchant_id == request.user.id` | Product update/delete (ownership check) |

### `apps/core/management/commands/seed_data.py` (399 lines)

Management command to seed the database with realistic medical equipment data.

**Command:** `python manage.py seed_data`

**What it creates:**

| Entity | Count | Details |
|--------|-------|---------|
| Merchants | 3 | MedEquip Tanzania, HealthTech Solutions, Precision Medical |
| Products | 13 | Across 6 categories (diagnostic, rehabilitation, life_support, mobility, sterilization, monitoring) |
| Product Images | 26 | 2 Unsplash URLs per product |
| Buyers | 3 | Juma (0694157749), Grace, Hamisi |
| Addresses | 3 | One per buyer, in Dar es Salaam, Arusha, Mwanza |
| Orders | 3 | One confirmed order per buyer |

**Idempotent:** Deactivates stale products not in the seed list on re-run.

**All passwords:** `TestPass123!`

---

## How This Directory Connects to the App

Every other app in the project depends on `apps.core`:

- **`responses.py`** — Every service function returns `envelope_ok()` or `envelope_error()`. This ensures all API responses have a consistent structure that the mobile app can reliably parse.
- **`exceptions.py`** — Wired into DRF globally via settings. Catches unhandled exceptions and formats them consistently.
- **`pagination.py`** — Used by product listing and order listing endpoints to handle large result sets.
- **`permissions.py`** — Applied to views via `permission_classes` to enforce role-based access control (buyer-only, merchant-only, owner-only).
- **`seed_data.py`** — Populates the database with realistic test data for development and QA.
