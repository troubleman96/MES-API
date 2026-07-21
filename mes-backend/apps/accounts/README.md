# apps/accounts/ — Authentication & User Management

Handles the complete user lifecycle: registration, login, JWT token management, phone OTP verification, password reset, and profile management.

---

## File Inventory

### `apps/accounts/__init__.py` (1 line)

Sets default app config to `AccountsConfig`.

### `apps/accounts/apps.py` (7 lines)

**Class:** `AccountsConfig(AppConfig)`
- `name = "apps.accounts"`
- `verbose_name = "Accounts"`

### `apps/accounts/models.py` (53 lines)

The custom user model for the entire project. Replaces Django's default `User`.

**Classes:**

#### `AccountManager(BaseUserManager)`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `create_user()` | `email`, `password`, `**extra_fields` | Creates a user, normalizes email, hashes password |
| `create_superuser()` | `email`, `password`, `**extra_fields` | Creates admin user with `is_staff=True`, `is_superuser=True` |

#### `Account(AbstractBaseUser, PermissionsMixin)`

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier (UUID v4) |
| `email` | EmailField | Unique | Login credential (USERNAME_FIELD) |
| `phone` | CharField(16) | Nullable | Tanzanian phone number |
| `phone_verified` | BooleanField | Default: False | Whether phone OTP was verified |
| `role` | CharField(10) | Choices: `buyer`, `merchant` | User role |
| `first_name` | CharField(100) | Required | User's first name |
| `last_name` | CharField(100) | Required | User's last name |
| `facility_name` | CharField(255) | Blank | Hospital/clinic name (buyers) |
| `business_name` | CharField(255) | Blank | Vendor company name (merchants) |
| `is_verified_merchant` | BooleanField | Default: False | Admin-approved merchant status |
| `is_active` | BooleanField | Default: True | Account active flag |
| `is_staff` | BooleanField | Default: False | Django admin access |
| `created_at` | DateTimeField | Auto | Account creation timestamp |

**Property:** `profile_complete` — Returns `True` if buyer has `facility_name` or merchant has `business_name`.

**Config:** `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = ["first_name", "last_name", "role"]`

**DB Table:** `accounts`

### `apps/accounts/serializers.py` (81 lines)

DRF serializers for input validation and output serialization.

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `RegisterSerializer` | `role`, `email`, `password`, `phone`, `first_name`, `last_name`, `facility_name`, `business_name` | Registration validation (password min 12 chars, role-specific fields) |
| `LoginSerializer` | `email`, `password` | Login validation |
| `AccountSerializer` | All profile fields + `profile_complete` | Read-only profile output |
| `AccountUpdateSerializer` | `first_name`, `last_name`, `phone`, `facility_name`, `business_name` | Profile update (partial) |
| `SendPhoneOTPSerializer` | `phone` | OTP request validation |
| `VerifyPhoneSerializer` | `otp` | OTP verification (6-digit) |
| `ForgotPasswordSerializer` | `email` | Password reset request |
| `ForgotPasswordConfirmSerializer` | `email`, `otp`, `new_password` | Password reset confirmation (password min 12 chars) |

**Validation rules:**
- `RegisterSerializer.validate_email()` — Checks uniqueness
- `RegisterSerializer.validate_password()` — Runs Django password validators
- `RegisterSerializer.validate()` — Enforces `facility_name` for buyers, `business_name` for merchants

### `apps/accounts/views.py` (102 lines)

DRF API views for all auth endpoints.

| View | HTTP Method | Auth Required | Description |
|------|------------|---------------|-------------|
| `RegisterView` | POST | No | Create new account |
| `LoginView` | POST | No | Email + password login |
| `RefreshTokenView` | POST | No | Rotate refresh token |
| `LogoutView` | POST | Yes | Invalidate refresh token |
| `ProfileView` | GET/PATCH | Yes | View/update profile |
| `SendPhoneOTPView` | POST | Yes | Send OTP to phone |
| `VerifyPhoneView` | POST | Yes | Verify phone with OTP |
| `ForgotPasswordView` | POST | No | Request password reset OTP |
| `ForgotPasswordConfirmView` | POST | No | Reset password with OTP |

### `apps/accounts/urls.py` (15 lines)

URL patterns under `/api/v1/auth/`:

| URL Pattern | View | Name |
|------------|------|------|
| `register/` | `RegisterView` | `register` |
| `login/` | `LoginView` | `login` |
| `refresh/` | `RefreshTokenView` | `token_refresh` |
| `logout/` | `LogoutView` | `logout` |
| `me/` | `ProfileView` | `profile` |
| `send-phone-otp/` | `SendPhoneOTPView` | `send_phone_otp` |
| `verify-phone/` | `VerifyPhoneView` | `verify_phone` |
| `forgot-password/` | `ForgotPasswordView` | `forgot_password` |
| `forgot-password/confirm/` | `ForgotPasswordConfirmView` | `forgot_password_confirm` |

### `apps/accounts/services.py` (147 lines)

Business logic layer for authentication operations.

| Function | Parameters | Description |
|----------|-----------|-------------|
| `register()` | `data` | Creates account, returns JWT tokens. 409 if email exists. |
| `login()` | `email`, `password` | Authenticates, returns tokens + role + expiry. 401 on bad creds. |
| `refresh_token()` | `refresh_token_str` | Rotates refresh token, returns new pair. 401 on invalid. |
| `get_profile()` | `user` | Returns serialized profile. |
| `update_profile()` | `user`, `data` | Partial update of profile fields. |
| `send_phone_otp()` | `user`, `phone` | Generates 6-digit OTP, sends SMS via SendAfrica, stores in Redis (15 min TTL). |
| `verify_phone()` | `user`, `otp` | Verifies OTP from Redis, sets `phone_verified=True`. |
| `forgot_password()` | `email` | Generates OTP, sends SMS if phone exists. Always returns generic message (prevents enumeration). |
| `forgot_password_confirm()` | `email`, `otp`, `new_password` | Verifies OTP, resets password. |

**OTP Storage:** Uses Django's Redis cache under key `otp:{user_id}:phone_verify` or `otp:{user_id}:forgot_password` with 900-second (15 min) TTL.

---

## How This Directory Connects to the App

- **Entry point for all users** — Every user must register and login through this app before accessing any protected endpoint.
- **JWT tokens** issued here are used by all other endpoints for authentication.
- **Phone verification** is required before checkout (enforced in `bookings/services.py`).
- **The `Account` model** is referenced by every other app as a foreign key (merchants, buyers, order participants).
- **`is_verified_merchant`** flag controls merchant trust level (used in equipment listings).
- **OTP flow** uses `apps.notifications.clients.SendAfricaClient` for SMS delivery and Redis for temporary storage.
