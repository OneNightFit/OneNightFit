"""Adapter data produk Catalog untuk Cart dan Checkout."""

import random

from catalog.models import Product

# Nama toko dummy karena API tidak menyediakan data toko
STORES = {
    "pebepuy67": "Pebepuy67",
    "safitrisda": "SafitriSDA",
    "rentabyrina": "RentaByRina",
    "kayacloset": "KayaCloset",
}

SIZES = ["S", "M", "L", "XL"]
LOCATIONS = ["Kutek", "Depok", "Jakarta", "Kukel", "Barel"]

# Harga minimum Rp5.000 dan maksimum Rp150.000
MIN_DAILY_RENT = 5000
MAX_DAILY_RENT = 150000

def daily_rent(price):
    rent = int(round(float(price), -3))
    return min(MAX_DAILY_RENT, max(MIN_DAILY_RENT, rent))

def to_product(product):
    """Membentuk data tampilan dengan ID tetap UUID dari Catalog Product."""
    rng = random.Random(str(product.pk))
    store = rng.choice(list(STORES))

    return {
        "id": product.pk,
        "name": product.name,
        "store": store,
        "store_name": STORES[store],
        "price": daily_rent(product.price),
        "size": product.size,
        "image": product.image or "",
        "available": True,
        "rating": round(rng.uniform(4.0, 5.0), 1),
        "reviews": rng.randint(5, 150),
        "location": rng.choice(LOCATIONS),
    }

def has_products():
    return Product.objects.exists()

def get_product(product_id):
    product = Product.objects.filter(pk=product_id).first()
    return to_product(product) if product else None

def get_products(ids):
    ids = list(ids)
    if not ids:
        return {}
    return {p.pk: to_product(p) for p in Product.objects.filter(pk__in=ids)}

def default_cart_products(limit=4):
    return [to_product(p) for p in Product.objects.order_by("name")[:limit]]

def recommended_products(exclude_ids=(), limit=5):
    products = list(Product.objects.exclude(pk__in=list(exclude_ids)))
    random.shuffle(products)
    return [to_product(p) for p in products[:limit]]