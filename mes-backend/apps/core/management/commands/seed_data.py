import random
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Account
from apps.addresses.models import Address
from apps.equipment.models import Product, ProductImage, AvailabilityBlock
from apps.cart.models import Cart, CartLine
from apps.bookings.models import OrderGroup, SubOrder, SubOrderLine


# ---------------------------------------------------------------------------
# Real medical-equipment image URLs (Unsplash / public domain)
# ---------------------------------------------------------------------------
EQUIPMENT_IMAGES = {
    "diagnostic": [
        "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600",
        "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=600",
        "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=600",
    ],
    "rehabilitation": [
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=600",
        "https://images.unsplash.com/photo-1581093450021-4a7360e9a6b5?w=600",
    ],
    "life_support": [
        "https://images.unsplash.com/photo-1584982751601-97dcc096659c?w=600",
        "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600",
        "https://images.unsplash.com/photo-1559757175-5700dde675bc?w=600",
    ],
    "mobility": [
        "https://images.unsplash.com/photo-1583946099379-f9c4c8b1aec0?w=600",
        "https://images.unsplash.com/photo-1581093450021-4a7360e9a6b5?w=600",
    ],
    "sterilization": [
        "https://images.unsplash.com/photo-1585435557343-3b092031a831?w=600",
        "https://images.unsplash.com/photo-1579154204601-01588f351e67?w=600",
    ],
    "monitoring": [
        "https://images.unsplash.com/photo-1551076805-e1869033e561?w=600",
        "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600",
        "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=600",
    ],
}

PRODUCTS_DATA = [
    # Merchant 1 – 3 products (diagnostic / monitoring)
    {
        "merchant_idx": 0,
        "name": "Digital Stethoscope 3M Littmann",
        "category": "diagnostic",
        "description": "Professional-grade digital stethoscope with active noise cancellation, Bluetooth connectivity, and 3M Littmann sound quality. Ideal for cardiology and pulmonary assessments.",
        "specs": {"brand": "3M Littmann", "model": "CORE 500", "weight_kg": 0.35, "warranty_months": 5},
        "daily_rate_tzs": 15000,
        "is_featured": True,
    },
    {
        "merchant_idx": 0,
        "name": "Portable Ultrasound Scanner GE Vscan Air",
        "category": "diagnostic",
        "description": "Handheld dual-probe ultrasound for rapid bedside imaging. FDA-cleared for cardiac, abdominal, and vascular examinations.",
        "specs": {"brand": "GE Healthcare", "model": "Vscan Air", "battery_hours": 6, "probe_types": "phased + linear"},
        "daily_rate_tzs": 45000,
        "is_featured": True,
    },
    {
        "merchant_idx": 0,
        "name": "Patient Monitor Contec CMS6000",
        "category": "monitoring",
        "description": "12.1-inch bedside patient monitor with ECG, SpO2, NIBP, temperature, and respiration rate. Touch-screen interface with trend storage.",
        "specs": {"brand": "Contec", "model": "CMS6000", "screen_inch": 12.1, "parameters": "ECG/SpO2/NIBP/Temp/Resp"},
        "daily_rate_tzs": 25000,
        "is_featured": False,
    },
    # Merchant 2 – 4 products (life_support / rehabilitation)
    {
        "merchant_idx": 1,
        "name": "Portable Oxygen Concentrator Inogen One G5",
        "category": "life_support",
        "description": "FAA-approved portable oxygen concentrator delivering up to 6 flow settings. Lightweight 2.5 kg with up to 6.5-hour battery life.",
        "specs": {"brand": "Inogen", "model": "One G5", "weight_kg": 2.5, "battery_hours": 6.5, "flow_settings": 6},
        "daily_rate_tzs": 35000,
        "is_featured": True,
    },
    {
        "merchant_idx": 1,
        "name": "CPAP Machine ResMed AirSense 11",
        "category": "life_support",
        "description": "Auto-titrating CPAP/BiPAP with built-in humidifier and cellular connectivity. Whisper-quiet operation at 25 dBA.",
        "specs": {"brand": "ResMed", "model": "AirSense 11", "noise_dba": 25, "pressure_range": "4-20 cmH2O"},
        "daily_rate_tzs": 30000,
        "is_featured": False,
    },
    {
        "merchant_idx": 1,
        "name": "Physiotherapy Ultrasound Unit Schwa Medico",
        "category": "rehabilitation",
        "description": "1 MHz and 3 MHz therapeutic ultrasound with pulsing modes. Ideal for deep tissue healing, joint stiffness, and sports injury rehab.",
        "specs": {"brand": "Schwa Medico", "model": "E 800", "frequencies": "1/3 MHz", "duty_cycle": "20-100%"},
        "daily_rate_tzs": 20000,
        "is_featured": False,
    },
    {
        "merchant_idx": 1,
        "name": "TENS / EMS Unit Beurer EM59",
        "category": "rehabilitation",
        "description": "Dual-channel TENS/EMS device with 6 preset programs and adjustable intensity. Includes 4 electrode pads for pain relief and muscle stimulation.",
        "specs": {"brand": "Beurer", "model": "EM59", "channels": 2, "programs": 6, "intensity_levels": 20},
        "daily_rate_tzs": 10000,
        "is_featured": False,
    },
    # Merchant 3 – 6 products (mobility / sterilization / monitoring / diagnostic)
    {
        "merchant_idx": 2,
        "name": "Electric Wheelchair Permobil M5 Corpus",
        "category": "mobility",
        "description": "Mid-wheel-drive power wheelchair with Corpus seating system, power tilt, recline, and elevating seat. Max speed 10 km/h, range 40 km.",
        "specs": {"brand": "Permobil", "model": "M5 Corpus", "max_speed_kmh": 10, "range_km": 40, "weight_kg": 136},
        "daily_rate_tzs": 50000,
        "is_featured": True,
    },
    {
        "merchant_idx": 2,
        "name": "Hospital-Grade Autoclave Melag Vacuklav 41B",
        "category": "sterilization",
        "description": "Class B vacuum autoclave with 18-litre chamber. 21 programmes, integrated thermal printer, and USB data logging.",
        "specs": {"brand": "Melag", "model": "Vacuklav 41B", "chamber_litres": 18, "cycle_time_min": 15, "programs": 21},
        "daily_rate_tzs": 40000,
        "is_featured": False,
    },
    {
        "merchant_idx": 2,
        "name": "Pulse Oximeter Masimo MightySat",
        "category": "monitoring",
        "description": "Fingertip pulse oximeter with Masimo SET® technology. Measures SpO2, pulse rate, respiration rate, and Pleth Variability Index.",
        "specs": {"brand": "Masimo", "model": "MightySat", "parameters": "SpO2/PR/RR/PVI", "battery_hours": 12},
        "daily_rate_tzs": 12000,
        "is_featured": True,
    },
    {
        "merchant_idx": 2,
        "name": "Infrared Thermometer Braun ThermoScan 7",
        "category": "diagnostic",
        "description": "Medical-grade ear thermometer with Age Precision technology. Pre-warmed tip for accuracy, night light, and 9 memories.",
        "specs": {"brand": "Braun", "model": "ThermoScan 7 IRT6520", "memory_slots": 9, "reading_time_sec": 3},
        "daily_rate_tzs": 8000,
        "is_featured": False,
    },
    {
        "merchant_idx": 2,
        "name": "Nebulizer Machine Omron CompAir NE-C28P",
        "category": "life_support",
        "description": "Compressor-driven nebulizer for asthma and respiratory therapy. Noise-reduced operation, suitable for adults and children.",
        "specs": {"brand": "Omron", "model": "CompAir NE-C28P", "nebulisation_rate_ml_min": 0.4, "noise_dba": 46},
        "daily_rate_tzs": 10000,
        "is_featured": False,
    },
    {
        "merchant_idx": 2,
        "name": "Mobility Walker Rollator Drive Medical Nitro",
        "category": "mobility",
        "description": "Lightweight aluminium rollator with seat, backrest, and cable brakes. Folds flat for transport. Weight capacity 136 kg.",
        "specs": {"brand": "Drive Medical", "model": "Nitro Euro", "weight_kg": 7.4, "max_user_kg": 136, "handle_height_cm": "81-89"},
        "daily_rate_tzs": 7000,
        "is_featured": False,
    },
]

BUYERS_DATA = [
    {
        "email": "juma.kitonda@mes.co.tz",
        "phone": "0694157749",
        "first_name": "Juma",
        "last_name": "Kitonda",
        "facility_name": "Kitonda Community Health Centre",
        "city": "Dar es Salaam",
        "address_line1": "Bagamoyo Road, Upanga",
        "district": "Kinondoni",
        "ward": "Upanga West",
    },
    {
        "email": "grace.mwamba@mes.co.tz",
        "phone": "0678123456",
        "first_name": "Grace",
        "last_name": "Mwamba",
        "facility_name": "Mwamba Women's Clinic",
        "city": "Arusha",
        "address_line1": "Serengeti Road, Njiro",
        "district": "Arusha City",
        "ward": "Njiro",
    },
    {
        "email": "hamisi.omari@mes.co.tz",
        "phone": "0623456789",
        "first_name": "Hamisi",
        "last_name": "Omari",
        "facility_name": "Omari Specialist Hospital",
        "city": "Mwanza",
        "address_line1": "Kenwal Road, Ilemela",
        "district": "Ilemela",
        "ward": "Ilemela",
    },
]

MERCHANTS_DATA = [
    {
        "email": "vendor1@mes.co.tz",
        "phone": "0628587749",
        "first_name": "Asha",
        "last_name": "Mwakio",
        "business_name": "MedEquip Tanzania Ltd",
    },
    {
        "email": "vendor2@mes.co.tz",
        "phone": "0654321098",
        "first_name": "Baraka",
        "last_name": "Nyerere",
        "business_name": "HealthTech Solutions Co",
    },
    {
        "email": "vendor3@mes.co.tz",
        "phone": "0611223344",
        "first_name": "Celestine",
        "last_name": "Mushi",
        "business_name": "Precision Medical Supplies",
    },
]


class Command(BaseCommand):
    help = "Seed the database with realistic medical equipment rental data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding database..."))

        # Deactivate any stale products not in our seed list
        seed_names = {p["name"] for p in PRODUCTS_DATA}
        stale = Product.objects.filter(is_active=True).exclude(name__in=seed_names)
        if stale.exists():
            self.stdout.write(f"  Deactivating {stale.count()} stale products")
            stale.update(is_active=False)

        merchants = self._create_merchants()
        products = self._create_products(merchants)
        buyers = self._create_buyers()
        self._create_addresses(buyers)
        self._create_orders(buyers, merchants, products)

        self.stdout.write(self.style.SUCCESS("\nDatabase seeded successfully"))
        self._print_summary(buyers, merchants, products)

    # ------------------------------------------------------------------
    def _create_merchants(self):
        merchants = []
        for data in MERCHANTS_DATA:
            acct, _ = Account.objects.update_or_create(
                email=data["email"],
                defaults={
                    "phone": data["phone"],
                    "phone_verified": True,
                    "role": "merchant",
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "business_name": data["business_name"],
                    "is_verified_merchant": True,
                },
            )
            acct.set_password("TestPass123!")
            acct.save()
            merchants.append(acct)
            self.stdout.write(f"  merchant: {acct.email}")
        return merchants

    def _create_products(self, merchants):
        products = []
        for pdata in PRODUCTS_DATA:
            merchant = merchants[pdata["merchant_idx"]]
            prod, _ = Product.objects.update_or_create(
                merchant=merchant,
                name=pdata["name"],
                defaults={
                    "category": pdata["category"],
                    "description": pdata["description"],
                    "specs": pdata["specs"],
                    "daily_rate_tzs": pdata["daily_rate_tzs"],
                    "is_featured": pdata["is_featured"],
                    "is_active": True,
                },
            )
            # attach images (skip duplicates)
            if prod.images.count() == 0:
                imgs = EQUIPMENT_IMAGES.get(pdata["category"], EQUIPMENT_IMAGES["diagnostic"])
                for idx, url in enumerate(imgs[:2]):
                    ProductImage.objects.create(product=prod, url=url, sort_order=idx)
            products.append(prod)
            self.stdout.write(f"  product: {prod.name}")
        return products

    def _create_buyers(self):
        buyers = []
        for data in BUYERS_DATA:
            acct, _ = Account.objects.update_or_create(
                email=data["email"],
                defaults={
                    "phone": data["phone"],
                    "phone_verified": True,
                    "role": "buyer",
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "facility_name": data["facility_name"],
                },
            )
            acct.set_password("TestPass123!")
            acct.save()
            buyers.append(acct)
            self.stdout.write(f"  buyer:   {acct.email}")
        return buyers

    def _create_addresses(self, buyers):
        for buyer, data in zip(buyers, BUYERS_DATA):
            Address.objects.update_or_create(
                account=buyer,
                label="Main Facility",
                defaults={
                    "facility_name": data["facility_name"],
                    "address_line1": data["address_line1"],
                    "city": data["city"],
                    "district": data["district"],
                    "ward": data["ward"],
                    "contact_name": f"{buyer.first_name} {buyer.last_name}",
                    "contact_phone": buyer.phone,
                    "address_type": "both",
                    "is_default": True,
                },
            )

    def _create_orders(self, buyers, merchants, products):
        """Create one sample order for each buyer so they have order history."""
        today = timezone.now().date()
        for i, buyer in enumerate(buyers):
            addr = buyer.addresses.first()
            if not addr:
                continue
            order_group = OrderGroup.objects.create(
                buyer=buyer,
                delivery_address=addr,
                billing_address=addr,
            )
            # each buyer gets 2 items from different merchants
            chosen = [products[i * 2], products[i * 2 + 1]]
            merchant_groups = {}
            for prod in chosen:
                merchant_groups.setdefault(prod.merchant_id, []).append(prod)

            for mid, prods in merchant_groups.items():
                merchant = Account.objects.get(id=mid)
                subtotal = sum(p.daily_rate_tzs * 3 for p in prods)
                sub = SubOrder.objects.create(
                    order_group=order_group,
                    merchant=merchant,
                    status="confirmed",
                    subtotal_tzs=subtotal,
                )
                for prod in prods:
                    SubOrderLine.objects.create(
                        sub_order=sub,
                        product=prod,
                        product_name_snapshot=prod.name,
                        daily_rate_snapshot_tzs=prod.daily_rate_tzs,
                        rental_start=today + timedelta(days=3),
                        rental_end=today + timedelta(days=6),
                        quantity=1,
                        line_total_tzs=prod.daily_rate_tzs * 3,
                    )
            self.stdout.write(f"  order for: {buyer.email}  ({order_group.id})")

    def _print_summary(self, buyers, merchants, products):
        self.stdout.write("\n" + "=" * 55)
        self.stdout.write(self.style.SUCCESS("SEED SUMMARY"))
        self.stdout.write("=" * 55)
        self.stdout.write(f"  Buyers:    {Account.objects.filter(role='buyer').count()}")
        self.stdout.write(f"  Merchants: {Account.objects.filter(role='merchant').count()}")
        self.stdout.write(f"  Products:  {Product.objects.count()}")
        self.stdout.write(f"  Images:    {ProductImage.objects.count()}")
        self.stdout.write(f"  Addresses: {Address.objects.count()}")
        self.stdout.write(f"  Orders:    {OrderGroup.objects.count()}")
        self.stdout.write("-" * 55)
        self.stdout.write("  All accounts password: TestPass123!")
        self.stdout.write("-" * 55)
        self.stdout.write("  BUYERS:")
        for b in buyers:
            self.stdout.write(f"    {b.email}  phone={b.phone}")
        self.stdout.write("  MERCHANTS:")
        for m in merchants:
            count = Product.objects.filter(merchant=m).count()
            self.stdout.write(f"    {m.email}  products={count}")
        self.stdout.write("=" * 55)
