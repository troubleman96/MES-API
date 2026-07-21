# apps/equipment/ — Product Catalog

Manages the medical equipment listings: products, images, availability blocks, and merchant profiles. This is the marketplace catalog that buyers browse and merchants manage.

---

## File Inventory

### `apps/equipment/__init__.py` (1 line)

Sets default app config to `EquipmentConfig`.

### `apps/equipment/apps.py` (7 lines)

**Class:** `EquipmentConfig(AppConfig)`
- `name = "apps.equipment"`
- `verbose_name = "Equipment"`

### `apps/equipment/models.py` (58 lines)

Three models that represent the product catalog.

#### `Product(models.Model)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `merchant` | ForeignKey(Account) | CASCADE, `related_name="products"` | Equipment owner |
| `name` | CharField(255) | Required | Equipment name |
| `category` | CharField(20) | Choices (see below) | Equipment category |
| `description` | TextField | Required | Detailed description |
| `specs` | JSONField | Default: `{}` | Flexible specifications (brand, model, weight, etc.) |
| `daily_rate_tzs` | PositiveIntegerField | Required | Rental price per day in Tanzanian Shillings |
| `is_featured` | BooleanField | Default: False | Featured listing flag |
| `is_active` | BooleanField | Default: True | Active/inactive (soft-delete support) |
| `created_at` | DateTimeField | Auto | Creation timestamp |

**Category choices:** `diagnostic`, `rehabilitation`, `life_support`, `mobility`, `sterilization`, `monitoring`

**Meta:** `db_table = "products"`, `ordering = ["-created_at"]`

#### `ProductImage(models.Model)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `product` | ForeignKey(Product) | CASCADE, `related_name="images"` | Parent product |
| `url` | URLField | Required | Image URL (e.g., Unsplash, MinIO) |
| `sort_order` | PositiveSmallIntegerField | Default: 0 | Display order |

**Meta:** `db_table = "product_images"`, `ordering = ["sort_order"]`

#### `AvailabilityBlock(models.Model)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `product` | ForeignKey(Product) | CASCADE, `related_name="blocked_ranges"` | Blocked product |
| `start_date` | DateField | Required | Block start date |
| `end_date` | DateField | Required | Block end date |
| `reason` | CharField(15) | Choices: `booked`, `maintenance` | Why the product is blocked |
| `sub_order` | ForeignKey(SubOrder) | Nullable, SET_NULL | Link to booking (if reason is "booked") |

**Meta:** `db_table = "availability_blocks"`, `ordering = ["start_date"]`

### `apps/equipment/serializers.py` (50 lines)

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `ProductImageSerializer` | `id`, `url`, `sort_order` | Image data |
| `ProductListSerializer` | `id`, `name`, `category`, `daily_rate_tzs`, `is_featured`, `is_active`, `created_at`, `images` | Product cards (list view) |
| `ProductDetailSerializer` | All fields + `merchant_name`, `merchant` (read-only) | Full product detail |
| `ProductCreateUpdateSerializer` | `name`, `category`, `description`, `specs`, `daily_rate_tzs`, `is_featured`, `is_active` | Create/update validation |
| `AvailabilityBlockSerializer` | `start_date`, `end_date` | Availability data (read-only) |

### `apps/equipment/views.py` (97 lines)

| View | HTTP Method | Auth Required | Role | Description |
|------|------------|---------------|------|-------------|
| `ProductListView` | GET | No | Any | Browse products (paginated, filterable) |
| `ProductListView` | POST | Yes | Merchant | Create new product listing |
| `ProductDetailView` | GET | No | Any | View product details |
| `ProductDetailView` | PUT | Yes | Merchant (owner) | Update product |
| `ProductDetailView` | DELETE | Yes | Merchant (owner) | Soft-delete product |
| `ProductAvailabilityView` | GET | No | Any | Check blocked date ranges |
| `MerchantDetailView` | GET | No | Any | View merchant profile |
| `MerchantProductListView` | GET | Yes | Merchant | List own products |

### `apps/equipment/urls.py` (11 lines)

URL patterns under `/api/v1/`:

| URL Pattern | View | Name |
|------------|------|------|
| `products/` | `ProductListView` | `product_list` |
| `products/<uuid:pk>/` | `ProductDetailView` | `product_detail` |
| `products/<uuid:pk>/availability/` | `ProductAvailabilityView` | `product_availability` |
| `merchants/<uuid:pk>/` | `MerchantDetailView` | `merchant_detail` |
| `merchants/me/products/` | `MerchantProductListView` | `merchant_product_list` |

### `apps/equipment/services.py` (92 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `list_products()` | `query_params` | Returns active products, filtered by `?category=` and `?search=` |
| `get_product()` | `product_id` | Returns product with images and merchant prefetched |
| `check_availability()` | `product_id` | Returns blocked date ranges |
| `get_merchant()` | `merchant_id` | Returns merchant Account or None |
| `create_listing()` | `user`, `data` | Creates product with merchant=user. Returns 201. |
| `update_listing()` | `user`, `product_id`, `data` | Partial update of own product |
| `delete_listing()` | `user`, `product_id` | Soft-deletes (sets `is_active=False`) |
| `list_merchant_products()` | `user` | Returns all products for authenticated merchant |

---

## How This Directory Connects to the App

- **Cart dependency** — When a buyer adds an item to cart (`cart/services.py`), it references a `Product` by UUID.
- **Checkout** — The checkout flow validates product availability by checking `AvailabilityBlock` for date conflicts.
- **Availability blocking** — When an order is confirmed (`bookings/services.py:checkout()`), `AvailabilityBlock` records are created for each rented item, preventing double-booking.
- **Order snapshots** — `SubOrderLine` stores `product_name_snapshot` and `daily_rate_snapshot_tzs` to preserve the product state at time of order.
- **Public browsing** — Product listing and detail views are `AllowAny`, enabling unauthenticated browsing of the catalog.
- **Merchant-only CRUD** — Creating, updating, and deleting products requires `IsMerchant` + `IsOwnerMerchant` permissions.
