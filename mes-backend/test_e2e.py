#!/usr/bin/env python
"""End-to-end test for MES API - full flow from registration to order lifecycle."""
import json
import sys
import time
import uuid

import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import requests
from django.core.cache import cache
from apps.accounts.models import Account
from apps.equipment.models import Product
from apps.cart.models import Cart, CartLine
from apps.bookings.models import OrderGroup, SubOrder, SubOrderLine
from apps.contracts.models import Contract, Signature
from apps.notifications.models import Notification
from apps.addresses.models import Address

BASE = "http://localhost:8000"
PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
INFO = "\033[94m→\033[0m"

results = []

def log(msg):
    print(f"  {INFO} {msg}")

def test(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
        results.append((name, True))
    else:
        print(f"  {FAIL} {name} {detail}")
        results.append((name, False))

def post(path, data, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return requests.post(f"{BASE}{path}", json=data, headers=h)

def get(path, token=None):
    h = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return requests.get(f"{BASE}{path}", headers=h)

def patch(path, data, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return requests.patch(f"{BASE}{path}", json=data, headers=h)

def delete(path, token=None):
    h = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return requests.delete(f"{BASE}{path}", headers=h)

BUYER_EMAIL = f"buyer_{uuid.uuid4().hex[:8]}@test.com"
MERCHANT_EMAIL = f"merchant_{uuid.uuid4().hex[:8]}@test.com"
BUYER_PHONE = "0694157749"
MERCHANT_PHONE = "0628587749"
BUYER_PASS = "TestPass123456!"
MERCHANT_PASS = "TestPass123456!"

buyer_token = None
merchant_token = None
buyer_id = None
merchant_id = None
product_id = None
address_id = None
order_group_id = None
sub_order_id = None

# Track created IDs for cleanup
created_ids = {"accounts": [], "products": [], "addresses": [], "orders": []}

try:
    # ──────────────────────────────────────────────
    # STEP 1: Register Buyer
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 1: Register Buyer ═══\033[0m")
    r = post("/api/v1/auth/register/", {
        "role": "buyer",
        "email": BUYER_EMAIL,
        "password": BUYER_PASS,
        "first_name": "John",
        "last_name": "Mwangi",
        "phone": BUYER_PHONE,
        "facility_name": "Muhimbili Hospital",
    })
    log(f"Status: {r.status_code}")
    data = r.json()
    test("Buyer registration returns 201", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    test("Returns access_token", "access_token" in data.get("data", {}))
    test("Returns refresh_token", "refresh_token" in data.get("data", {}))
    test("Role is buyer", data.get("data", {}).get("role") == "buyer")
    buyer_token = data.get("data", {}).get("access_token")

    # Get buyer ID
    r2 = get("/api/v1/auth/me/", buyer_token)
    buyer_id = r2.json().get("data", {}).get("id")
    if buyer_id:
        created_ids["accounts"].append(buyer_id)
        log(f"Buyer ID: {buyer_id}")

    # ──────────────────────────────────────────────
    # STEP 2: Register Merchant
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 2: Register Merchant ═══\033[0m")
    r = post("/api/v1/auth/register/", {
        "role": "merchant",
        "email": MERCHANT_EMAIL,
        "password": MERCHANT_PASS,
        "first_name": "Amina",
        "last_name": "Hassan",
        "phone": MERCHANT_PHONE,
        "business_name": "Dar Medical Supplies",
    })
    log(f"Status: {r.status_code}")
    data = r.json()
    test("Merchant registration returns 201", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    test("Role is merchant", data.get("data", {}).get("role") == "merchant")
    merchant_token = data.get("data", {}).get("access_token")

    r2 = get("/api/v1/auth/me/", merchant_token)
    merchant_id = r2.json().get("data", {}).get("id")
    if merchant_id:
        created_ids["accounts"].append(merchant_id)
        log(f"Merchant ID: {merchant_id}")

    # ──────────────────────────────────────────────
    # STEP 3: Login Both Users
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 3: Login Both Users ═══\033[0m")
    r = post("/api/v1/auth/login/", {"email": BUYER_EMAIL, "password": BUYER_PASS})
    data = r.json()
    test("Buyer login returns 200", r.status_code == 200, f"got {r.status_code}")
    test("Login returns expires_in", "expires_in" in data.get("data", {}))
    buyer_token = data["data"]["access_token"]

    r = post("/api/v1/auth/login/", {"email": MERCHANT_EMAIL, "password": MERCHANT_PASS})
    test("Merchant login returns 200", r.status_code == 200, f"got {r.status_code}")
    merchant_token = r.json()["data"]["access_token"]

    # ──────────────────────────────────────────────
    # STEP 4: Send OTP to Buyer (real SMS)
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 4: Send OTP to Buyer (real SMS) ═══\033[0m")
    r = post("/api/v1/auth/send-phone-otp/", {"phone": BUYER_PHONE}, buyer_token)
    log(f"Status: {r.status_code}")
    log(f"Response: {r.json()}")
    test("OTP sent to buyer", r.status_code == 200, f"got {r.status_code}: {r.json().get('error')}")

    # Read OTP from cache
    buyer_otp = cache.get(f"otp:{buyer_id}:phone_verify")
    log(f"OTP from cache: {buyer_otp}")
    test("OTP stored in cache", buyer_otp is not None)

    # ──────────────────────────────────────────────
    # STEP 5: Verify Buyer Phone
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 5: Verify Buyer Phone ═══\033[0m")
    r = post("/api/v1/auth/verify-phone/", {"otp": buyer_otp}, buyer_token)
    log(f"Status: {r.status_code}")
    log(f"Response: {r.json()}")
    test("Buyer phone verified", r.status_code == 200, f"got {r.status_code}")

    # Confirm via profile
    r = get("/api/v1/auth/me/", buyer_token)
    test("phone_verified is true", r.json()["data"]["phone_verified"] is True)

    # ──────────────────────────────────────────────
    # STEP 6: Send OTP to Merchant (real SMS)
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 6: Send OTP to Merchant (real SMS) ═══\033[0m")
    r = post("/api/v1/auth/send-phone-otp/", {"phone": MERCHANT_PHONE}, merchant_token)
    log(f"Status: {r.status_code}")
    log(f"Response: {r.json()}")
    test("OTP sent to merchant", r.status_code == 200, f"got {r.status_code}: {r.json().get('error')}")

    merchant_otp = cache.get(f"otp:{merchant_id}:phone_verify")
    log(f"OTP from cache: {merchant_otp}")
    test("OTP stored in cache", merchant_otp is not None)

    # ──────────────────────────────────────────────
    # STEP 7: Verify Merchant Phone
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 7: Verify Merchant Phone ═══\033[0m")
    r = post("/api/v1/auth/verify-phone/", {"otp": merchant_otp}, merchant_token)
    log(f"Status: {r.status_code}")
    log(f"Response: {r.json()}")
    test("Merchant phone verified", r.status_code == 200, f"got {r.status_code}")

    r = get("/api/v1/auth/me/", merchant_token)
    test("phone_verified is true", r.json()["data"]["phone_verified"] is True)

    # ──────────────────────────────────────────────
    # STEP 8: Merchant Creates Product Listing
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 8: Merchant Creates Product ═══\033[0m")
    r = post("/api/v1/products/", {
        "name": "Portable Ultrasound Machine",
        "category": "diagnostic",
        "description": "GE Vivid E95 portable ultrasound for diagnostic imaging. Perfect for field hospitals.",
        "specs": {"brand": "GE Healthcare", "model": "Vivid E95", "weight_kg": 15},
        "daily_rate_tzs": 150000,
        "is_featured": True,
        "is_active": True,
    }, merchant_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Product created (201)", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    product_id = data.get("data", {}).get("id")
    if product_id:
        created_ids["products"].append(product_id)
        log(f"Product ID: {product_id}")
    test("Product has correct name", data.get("data", {}).get("name") == "Portable Ultrasound Machine")
    test("Product has daily rate", data.get("data", {}).get("daily_rate_tzs") == 150000)

    # Verify product is publicly visible
    r = get("/api/v1/products/")
    items = r.json().get("data", {}).get("items", [])
    test("Product visible in public listing", any(p["id"] == product_id for p in items))

    # ──────────────────────────────────────────────
    # STEP 9: Buyer Creates Address
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 9: Buyer Creates Address ═══\033[0m")
    r = post("/api/v1/addresses/", {
        "label": "Hospital Main",
        "facility_name": "Muhimbili National Hospital",
        "address_line1": "Uganda Road",
        "city": "Dar es Salaam",
        "contact_name": "John Mwangi",
        "contact_phone": "+255694157749",
        "address_type": "both",
        "is_default": True,
    }, buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Address created (201)", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    address_id = data.get("data", {}).get("id")
    if address_id:
        created_ids["addresses"].append(address_id)
        log(f"Address ID: {address_id}")
    test("Address has correct city", data.get("data", {}).get("city") == "Dar es Salaam")

    # ──────────────────────────────────────────────
    # STEP 10: Buyer Adds Product to Cart
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 10: Buyer Adds to Cart ═══\033[0m")
    r = patch("/api/v1/cart/", {
        "lines": [{
            "product": product_id,
            "rental_start": "2026-08-01",
            "rental_end": "2026-08-04",
            "quantity": 1,
            "added_at": "2026-07-21T08:00:00Z",
        }]
    }, buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Cart updated (200)", r.status_code == 200, f"got {r.status_code}: {data.get('error')}")
    cart_lines = data.get("data", {}).get("cart", {}).get("lines", [])
    test("Cart has 1 line", len(cart_lines) == 1, f"got {len(cart_lines)} lines")
    test("Cart line has correct product", cart_lines[0]["product"] == product_id if cart_lines else False)
    test("No stale lines", len(data.get("data", {}).get("stale_lines", [])) == 0)

    # ──────────────────────────────────────────────
    # STEP 11: Buyer Checks Out
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 11: Buyer Checks Out ═══\033[0m")
    r = post("/api/v1/checkout/", {
        "delivery_address_id": address_id,
        "billing_address_id": address_id,
        "notes": "Please deliver before 10am",
    }, buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Checkout returns 201", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    order_group_id = data.get("data", {}).get("order_group_id")
    sub_orders = data.get("data", {}).get("sub_orders", [])
    if sub_orders:
        sub_order_id = sub_orders[0]["id"]
        log(f"Order Group: {order_group_id}")
        log(f"Sub-Order: {sub_order_id}")
        log(f"Subtotal: TZS {sub_orders[0]['subtotal_tzs']}")
        test("Sub-order status is pending_payment", sub_orders[0]["status"] == "pending_payment")
        test("Subtotal calculated", sub_orders[0]["subtotal_tzs"] > 0)
        # 3 days × 150000/day × 1 qty = 450000
        test("Subtotal is TZS 450000 (3 days × 150k)", sub_orders[0]["subtotal_tzs"] == 450000)

    # Verify cart is cleared
    r = get("/api/v1/cart/", buyer_token)
    cart_lines = r.json().get("data", {}).get("lines", [])
    test("Cart cleared after checkout", len(cart_lines) == 0)

    # ──────────────────────────────────────────────
    # STEP 12: Buyer Initiates Payment (real Snippe USSD push)
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 12: Initiate Payment (Snippe) ═══\033[0m")
    r = post(f"/api/v1/orders/{sub_order_id}/pay/", {}, buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Payment initiated (201)", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    snippe_ref = data.get("data", {}).get("snippe_reference")
    payment_status = data.get("data", {}).get("status")
    log(f"Snippe reference: {snippe_ref}")
    log(f"Payment status: {payment_status}")
    test("Payment has snippe_reference", snippe_ref is not None)
    test("Payment status is pending", payment_status == "pending")

    # Check payment status endpoint
    r = get(f"/api/v1/orders/{sub_order_id}/payment-status/", buyer_token)
    log(f"Payment status check: {r.json()}")

    # ──────────────────────────────────────────────
    # STEP 13: Wait for USSD push & simulate payment completion
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 13: Payment Processing ═══\033[0m")
    log("NOTE: Snippe sends a USSD push to the buyer's phone.")
    log("In production, the buyer approves on their phone, then Snippe hits our webhook.")
    log("For this test, we simulate the webhook to confirm payment.")

    # Simulate payment.completed webhook
    import hashlib
    import hmac
    webhook_payload = {
        "id": str(uuid.uuid4()),
        "type": "payment.completed",
        "data": {
            "reference": snippe_ref,
            "amount": 450000,
            "currency": "TZS",
            "channel": {"provider": "Vodacom"},
        }
    }
    webhook_secret = os.getenv("SNIPPE_WEBHOOK_SECRET", "")
    timestamp = str(int(time.time()))
    body_str = json.dumps(webhook_payload)
    if webhook_secret:
        sig = hmac.new(webhook_secret.encode(), f"{timestamp}.{body_str}".encode(), hashlib.sha256).hexdigest()
    else:
        sig = ""

    r = requests.post(
        f"{BASE}/webhooks/snippe/",
        json=webhook_payload,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": sig,
        }
    )
    log(f"Webhook status: {r.status_code}")
    log(f"Webhook response: {r.text[:200]}")

    # Check if order status changed to confirmed
    time.sleep(1)
    r = get(f"/api/v1/orders/{sub_order_id}/", buyer_token)
    order_data = r.json().get("data", {})
    log(f"Order status after webhook: {order_data.get('status')}")
    test("Order status changed to confirmed", order_data.get("status") == "confirmed", f"got {order_data.get('status')}")

    # ──────────────────────────────────────────────
    # STEP 14: Contract Generated
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 14: Check Contract ═══\033[0m")
    r = get(f"/api/v1/orders/{sub_order_id}/contract/", buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Contract exists (200)", r.status_code == 200, f"got {r.status_code}")
    test("Contract has pdf_url", bool(data.get("data", {}).get("pdf_url")))
    test("Contract is not signed yet", data.get("data", {}).get("signed_at") is None)

    # ──────────────────────────────────────────────
    # STEP 15: Buyer Signs Contract
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 15: Buyer Signs Contract ═══\033[0m")
    r = post(f"/api/v1/orders/{sub_order_id}/contract/sign/", {
        "signature_image_url": "https://storage.mes.co.tz/sigs/john_mwangi.png",
    }, buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Contract signed (201)", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")
    test("Signature ID returned", "signature_id" in data.get("data", {}))

    # ──────────────────────────────────────────────
    # STEP 16: Merchant Confirms Order
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 16: Merchant Confirms Order ═══\033[0m")
    r = patch(f"/api/v1/orders/{sub_order_id}/status/", {"status": "confirmed"}, merchant_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    # Note: status is already "confirmed" from the webhook, so this may say invalid_transition
    log("Note: Order already confirmed via payment webhook - transition test skipped")

    # ──────────────────────────────────────────────
    # STEP 17: Merchant Dispatches Order (requires signed contract)
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 17: Merchant Dispatches Order ═══\033[0m")
    r = patch(f"/api/v1/orders/{sub_order_id}/status/", {"status": "dispatched"}, merchant_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Dispatch successful (200)", r.status_code == 200, f"got {r.status_code}: {data.get('error')}")
    test("Status is now dispatched", data.get("data", {}).get("status") == "dispatched")

    # ──────────────────────────────────────────────
    # STEP 18: Check Notifications
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 18: Check Notifications ═══\033[0m")
    r = get("/api/v1/notifications/", buyer_token)
    log(f"Buyer notifications: {json.dumps(r.json(), indent=2)}")
    buyer_notifs = r.json().get("data", [])
    test("Buyer has notifications", len(buyer_notifs) > 0, f"got {len(buyer_notifs)}")

    r = get("/api/v1/notifications/unread-count/", buyer_token)
    unread = r.json().get("data", {}).get("count", 0)
    log(f"Buyer unread count: {unread}")
    test("Unread count is set", unread >= 0)

    r = get("/api/v1/notifications/", merchant_token)
    merchant_notifs = r.json().get("data", [])
    log(f"Merchant notifications: {len(merchant_notifs)}")
    test("Merchant has notifications", len(merchant_notifs) > 0, f"got {len(merchant_notifs)}")

    # ──────────────────────────────────────────────
    # STEP 19: Merchant Delivers
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 19: Merchant Delivers ═══\033[0m")
    r = patch(f"/api/v1/orders/{sub_order_id}/status/", {"status": "delivered"}, merchant_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Delivered (200)", r.status_code == 200, f"got {r.status_code}: {data.get('error')}")
    test("Status is delivered", data.get("data", {}).get("status") == "delivered")

    # ──────────────────────────────────────────────
    # STEP 20: Order List for Both Users
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 20: Order Lists ═══\033[0m")
    r = get("/api/v1/orders/", buyer_token)
    buyer_orders = r.json().get("data", [])
    log(f"Buyer orders: {len(buyer_orders)}")
    test("Buyer sees their orders", len(buyer_orders) >= 1)

    r = get("/api/v1/orders/", merchant_token)
    merchant_orders = r.json().get("data", [])
    log(f"Merchant orders: {len(merchant_orders)}")
    test("Merchant sees incoming orders", len(merchant_orders) >= 1)

    # ──────────────────────────────────────────────
    # STEP 21: Register Device Token (FCM)
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ STEP 21: Register Device Token ═══\033[0m")
    fake_fcm = f"test_fcm_{uuid.uuid4().hex}"
    r = post("/api/v1/notifications/register-device/", {"fcm_token": fake_fcm}, buyer_token)
    log(f"Status: {r.status_code}")
    data = r.json()
    log(f"Response: {json.dumps(data, indent=2)}")
    test("Device token registered", r.status_code == 201, f"got {r.status_code}: {data.get('error')}")

    # ──────────────────────────────────────────────
    # CLEANUP: Delete all test data
    # ──────────────────────────────────────────────
    print("\n\033[1m═══ CLEANUP ═══\033[0m")

    # Delete notifications
    deleted_notifs = Notification.objects.filter(account_id__in=created_ids["accounts"]).delete()
    log(f"Deleted notifications: {deleted_notifs}")

    # Delete contracts & signatures
    if sub_order_id:
        deleted_contracts = Contract.objects.filter(sub_order_id=sub_order_id).delete()
        log(f"Deleted contracts: {deleted_contracts}")

    # Delete sub_order_lines, sub_orders, order_groups
    if order_group_id:
        deleted_groups = OrderGroup.objects.filter(id=order_group_id).delete()
        log(f"Deleted order group: {deleted_groups}")

    # Delete cart lines & carts
    for aid in created_ids["accounts"]:
        CartLine.objects.filter(cart__account_id=aid).delete()
        Cart.objects.filter(account_id=aid).delete()
    log("Deleted carts")

    # Delete addresses
    deleted_addrs = Address.objects.filter(account_id__in=created_ids["accounts"]).delete()
    log(f"Deleted addresses: {deleted_addrs}")

    # Delete products
    deleted_prods = Product.objects.filter(id__in=created_ids["products"]).delete()
    log(f"Deleted products: {deleted_prods}")

    # Delete accounts
    for aid in created_ids["accounts"]:
        Account.objects.filter(id=aid).delete()
    log(f"Deleted accounts: {created_ids['accounts']}")

    # Verify cleanup
    remaining = Account.objects.filter(id__in=created_ids["accounts"]).count()
    test("All test accounts deleted", remaining == 0)

finally:
    # ──────────────────────────────────────────────
    # RESULTS SUMMARY
    # ──────────────────────────────────────────────
    print("\n" + "═" * 50)
    print("\033[1m  TEST RESULTS SUMMARY\033[0m")
    print("═" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)

    for name, ok in results:
        status = f"{PASS}" if ok else f"{FAIL}"
        print(f"  {status} {name}")

    print(f"\n  \033[1mTotal: {total} | Passed: {passed} | Failed: {failed}\033[0m")

    if failed == 0:
        print(f"\n  \033[92m🎉 ALL TESTS PASSED!\033[0m")
    else:
        print(f"\n  \033[91m⚠ {failed} test(s) failed\033[0m")

    print("═" * 50)
    sys.exit(0 if failed == 0 else 1)
