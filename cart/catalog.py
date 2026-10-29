"""Adapter data produk Catalog untuk Cart dan Checkout."""

import random

from catalog.models import Product
from .models import Rental, local_rental_date

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

def unavailable_product_ids(product_ids=None):
    rentals = Rental.objects.filter(rental_date=local_rental_date())
    if product_ids is not None:
        rentals = rentals.filter(product_uuid__in=product_ids)
    return set(rentals.values_list("product_uuid", flat=True))

def to_product(product, unavailable_ids=None):
    """Membentuk data tampilan dengan ID tetap UUID dari Catalog Product."""
    if unavailable_ids is None:
        unavailable_ids = unavailable_product_ids([product.pk])
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
        "available": product.pk not in unavailable_ids,
        "rating": round(rng.uniform(4.0, 5.0), 1),
        "reviews": rng.randint(5, 150),
        "location": rng.choice(LOCATIONS),
    }

def has_products():
    return Product.objects.exclude(pk__in=unavailable_product_ids()).exists()

def get_product(product_id):
    product = Product.objects.filter(pk=product_id).first()
    if not product:
        return None
    return to_product(product, unavailable_product_ids([product.pk]))

def get_products(ids):
    ids = list(ids)
    if not ids:
        return {}
    unavailable = unavailable_product_ids(ids)
    return {p.pk: to_product(p, unavailable) for p in Product.objects.filter(pk__in=ids)}

def default_cart_products(limit=4):
    unavailable = unavailable_product_ids()
    return [to_product(p, unavailable) for p in Product.objects.exclude(pk__in=unavailable).order_by("name")[:limit]]

def recommended_products(exclude_ids=(), limit=5):
    unavailable = unavailable_product_ids()
    products = list(Product.objects.exclude(pk__in=[*exclude_ids, *unavailable]))
    random.shuffle(products)
    return [to_product(p, unavailable) for p in products[:limit]]
