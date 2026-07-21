# apps/notifications/ — Notifications & Push

Handles in-app notifications, SMS delivery via SendAfrica, and push notifications via Firebase Cloud Messaging (FCM).

---

## File Inventory

### `apps/notifications/__init__.py` (1 line)

Sets default app config to `NotificationsConfig`.

### `apps/notifications/apps.py` (7 lines)

**Class:** `NotificationsConfig(AppConfig)`
- `name = "apps.notifications"`
- `verbose_name = "Notifications"`

### `apps/notifications/models.py` (34 lines)

#### `Notification(models.Model)`

In-app notification record.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `account` | ForeignKey(Account) | CASCADE, `related_name="notifications"` | Recipient |
| `type` | CharField(20) | Choices (see below) | Notification category |
| `title` | CharField(255) | Required | Short title |
| `body` | TextField | Required | Full message body |
| `read_at` | DateTimeField | Nullable | When the notification was read (null = unread) |
| `created_at` | DateTimeField | Auto | Creation timestamp |

**Type choices:** `order_confirmed`, `payment_received`, `return_due`, `merchant_message`

**Meta:** `db_table = "notifications"`, `ordering = ["-created_at"]`

#### `DeviceToken(models.Model)`

FCM device token registration.

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | UUIDField | Primary key | Unique identifier |
| `account` | ForeignKey(Account) | CASCADE, `related_name="device_tokens"` | Device owner |
| `fcm_token` | CharField(255) | Unique | Firebase Cloud Messaging token |
| `registered_at` | DateTimeField | Auto | Registration timestamp |

**Meta:** `db_table = "device_tokens"`

### `apps/notifications/serializers.py` (16 lines)

| Serializer | Fields | Purpose |
|-----------|--------|---------|
| `NotificationSerializer` | `id`, `type`, `title`, `body`, `read_at`, `created_at` | Notification data |
| `DeviceTokenSerializer` | `id`, `fcm_token`, `registered_at` | Device token data |

### `apps/notifications/views.py` (42 lines)

| View | HTTP Method | Auth Required | Description |
|------|------------|---------------|-------------|
| `NotificationListView` | GET | Yes | List all notifications |
| `NotificationUnreadCountView` | GET | Yes | Get count of unread notifications |
| `NotificationReadView` | PATCH | Yes | Mark a single notification as read |
| `NotificationReadAllView` | POST | Yes | Mark all notifications as read |
| `DeviceTokenView` | POST | Yes | Register FCM device token |

### `apps/notifications/urls.py` (11 lines)

URL patterns under `/api/v1/notifications/`:

| URL Pattern | View | Name |
|------------|------|------|
| `""` | `NotificationListView` | `notification_list` |
| `unread-count/` | `NotificationUnreadCountView` | `notification_unread_count` |
| `<uuid:pk>/read/` | `NotificationReadView` | `notification_read` |
| `read-all/` | `NotificationReadAllView` | `notification_read_all` |
| `register-device/` | `DeviceTokenView` | `register_device` |

### `apps/notifications/services.py` (91 lines)

| Function | Parameters | Description |
|----------|-----------|-------------|
| `notify()` | `event_type`, `account`, `context` | Creates notification + sends FCM + SMS |
| `_send_fcm()` | `account`, `title`, `body` | Sends push notification via Firebase |
| `list_notifications()` | `user` | Returns all notifications for user |
| `unread_count()` | `user` | Returns count of unread notifications |
| `mark_read()` | `user`, `notification_id` | Marks single notification as read |
| `mark_all_read()` | `user` | Marks all notifications as read |
| `register_device()` | `user`, `fcm_token` | Registers or retrieves FCM device token |

**`notify()` flow:**
1. Creates `Notification` record in database
2. Calls `_send_fcm()` to send push notification
3. For event types `order_confirmed`, `payment_received`, `return_due`: sends SMS via SendAfrica if phone is available

**`_send_fcm()` flow:**
1. Gets all `DeviceToken` records for the account
2. Initializes Firebase Admin SDK (if not already initialized)
3. Creates `MulticastMessage` with all device tokens
4. Sends via `messaging.send_each_for_multicast()`
5. Silently catches exceptions (graceful degradation)

### `apps/notifications/clients.py` (29 lines)

HTTP client for the SendAfrica SMS gateway.

**Class:** `SendAfricaClient`

| Method | Parameters | Description |
|--------|-----------|-------------|
| `__init__()` | — | Reads `SENDAFRICA_API_KEY` from Django settings |
| `send_sms()` | `phone_number`, `message` | POSTs to `https://api.sendafrica.online/v1/sms/` with `X-API-Key` header. Returns `True` on success (200/201/202). |

**Request format:**
```json
{
  "to": "0694157749",
  "message": "Your MES verification code is: 123456. Valid for 15 minutes."
}
```

**Headers:**
```
X-API-Key: SA-d82101...
Content-Type: application/json
```

---

## How This Directory Connects to the App

- **Order lifecycle notifications** — When order status changes (confirmed, dispatched, delivered), `notify()` should be called to alert the buyer and merchant.
- **OTP delivery** — The `accounts` app uses `SendAfricaClient` directly for phone verification OTPs and password reset codes.
- **Multi-channel delivery** — Each notification is delivered via up to 3 channels: database (in-app), SMS (SendAfrica), and push (FCM).
- **Device registration** — The mobile app calls `register-device/` after login to enable push notifications on that device.
- **Read tracking** — The `read_at` field enables the mobile app to show unread badges and mark items as read.
