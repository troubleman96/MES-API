# apps/contracts/ — Rental Agreements

Handles PDF rental agreement generation, contract retrieval, and digital signature collection for equipment rental transactions.

---

## File Inventory

### `apps/contracts/__init__.py` (1 line)

Sets default app config to `ContractsConfig`.

### `apps/contracts/apps.py` (7 lines)

**Class:** `ContractsConfig(AppConfig)`
- `name = "apps.contracts"`
- `verbose_name = "Contracts"`

### `apps/contracts/models.py` (24 lines)

#### `Contract(models.Model)`

One contract per sub-order, generated after payment confirmation.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `sub_order` | OneToOneField(SubOrder) | CASCADE, `related_name="contract"` | Associated order |
| `pdf_url` | URLField | Required | Path to generated PDF |
| `generated_at` | DateTimeField | Auto | When the contract was generated |

**Meta:** `db_table = "contracts"`

#### `Signature(models.Model)`

Digital signature captured from the buyer.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `contract` | ForeignKey(Contract) | CASCADE, `related_name="signatures"` | Contract being signed |
| `signer` | ForeignKey(Account) | PROTECT | User who signed |
| `signature_image_url` | URLField | Required | URL of signature image |
| `signed_at` | DateTimeField | Auto | When the signature was captured |

**Meta:** `db_table = "signatures"`

### `apps/contracts/serializers.py` (29 lines)

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `ContractSerializer` | `id`, `sub_order`, `pdf_url`, `generated_at` | Basic contract data |
| `SignatureSerializer` | `id`, `contract`, `signer`, `signer_name` (read-only), `signature_image_url`, `signed_at` | Signature data |
| `ContractDetailSerializer` | All contract fields + nested `signatures` | Full contract with signatures |
| `SignContractSerializer` | `signature_image_url` | Input for signing |

### `apps/contracts/views.py` (21 lines)

| View | HTTP Method | Auth Required | Role | Description |
|------|------------|---------------|------|-------------|
| `ContractView` | GET | Yes | Buyer/Merchant | Retrieve contract for an order |
| `ContractSignView` | POST | Yes | Buyer | Sign the contract |

### `apps/contracts/urls.py` (8 lines)

URL patterns under `/api/v1/`:

| URL Pattern | View | Name |
|------------|------|------|
| `orders/<uuid:pk>/contract/` | `ContractView` | `contract` |
| `orders/<uuid:pk>/contract/sign/` | `ContractSignView` | `contract_sign` |

### `apps/contracts/services.py` (136 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `generate_contract_pdf()` | `sub_order` | Generates A4 PDF rental agreement using ReportLab |
| `get_contract()` | `user`, `sub_order_id` | Retrieves contract with ownership verification |
| `sign_contract()` | `user`, `sub_order_id`, `data` | Captures buyer's digital signature |

**PDF Generation (`generate_contract_pdf`):**
1. Creates or gets Contract for the sub-order (idempotent)
2. If PDF already exists, returns immediately
3. Generates A4 PDF with ReportLab containing:
   - Title: "Medical Equipment Rental Agreement"
   - Contract reference: `MES-{sub_order_id[:8]}`
   - Date
   - Buyer information (name, facility, email)
   - Rental items (product name, quantity, daily rate, period, line total)
   - Total amount
   - Terms text
   - Signature lines for buyer and merchant
4. Saves PDF to `contracts/{sub_order_id}/agreement.pdf`
5. Updates Contract.pdf_url

**Contract retrieval (`get_contract`):**
- Buyers can only see their own orders' contracts
- Merchants can only see contracts for orders they fulfill
- Returns 403 for unauthorized access, 404 if not found

**Contract signing (`sign_contract`):**
- Only buyers can sign (403 if merchant)
- Verifies buyer owns the order
- Prevents duplicate signing (400 if already signed)
- Creates Signature record with image URL

---

## How This Directory Connects to the App

- **Payment-triggered generation** — Contracts are automatically generated when a payment completes (`payments/services.py:handle_webhook()` calls `generate_contract_pdf()`).
- **Dispatch gate** — The order status machine (`bookings/services.py:update_order_status()`) requires a signed contract before allowing transition to `dispatched`.
- **Buyer-only signing** — Only the buyer signs the contract. The merchant's signature line is present in the PDF but the API only captures the buyer's digital signature.
- **PDF storage** — Generated PDFs are stored at `contracts/{sub_order_id}/agreement.pdf` (local filesystem or S3/MinIO when configured).
- **Legal compliance** — The contract ensures both parties have a written agreement before equipment is dispatched.
