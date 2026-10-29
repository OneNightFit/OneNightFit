"""
Adapter produk untuk Cart dan Checkout.

Menggunakan produk Fake Store API yang sama dengan Inspo,
yang sudah diimpor ke tabel inspo.Post.

Data toko, ukuran, rating, ulasan, lokasi, dan harga sewa
dibuat sebagai dummy karena tidak tersedia dari API.
Nilainya tetap sama untuk setiap produk agar Cart dan Checkout konsisten.

Jika nanti ada model Product asli, cukup ubah file ini.
"""

import random


# Nama toko dummy karena API tidak menyediakan data toko
STORES = {
    "pebepuy67": "Pebepuy67",
    "safitrisda": "SafitriSDA",
    "rentabyrina": "RentaByRina",
    "kayacloset": "KayaCloset",
}

SIZES = ["S", "M", "L", "XL"]
LOCATIONS = ["Kutek", "Depok", "Jakarta", "Kukel", "Barel"]

# Konversi harga API dari USD ke harga sewa harian dalam rupiah dengan dikali 500
# Harga minimum Rp5.000 dan maksimum Rp150.000
RENT_PER_USD = 500
MIN_DAILY_RENT = 5000
MAX_DAILY_RENT = 150000

def daily_rent(usd_price):
    rent = int(round(float(usd_price) * RENT_PER_USD, -3))
    return min(MAX_DAILY_RENT, max(MIN_DAILY_RENT, rent))

def to_product(post):
    """Menggunakan ID produk agar data dummy tetap konsisten"""
    rng = random.Random(post.external_id)
    store = rng.choice(list(STORES))

    return {
        "id": post.pk,
        "name": post.title,
        "store": store,
        "store_name": STORES[store],
        "price": daily_rent(post.price),
        "size": rng.choice(SIZES),
        "image": post.image_src,
        "available": True,
        "rating": round(rng.uniform(4.0, 5.0), 1),
        "reviews": rng.randint(5, 150),
        "location": rng.choice(LOCATIONS),
    }

def api_posts():
    from inspo.models import Post # Import di dalam fungsi modul aman diimpor tanpa Django
    return Post.objects.filter(external_id__isnull=False, price__isnull=False)

def get_product(product_id):
    """Mengambil satu produk berdasarkan ID"""
    post = api_posts().filter(pk=product_id).first()
    return to_product(post) if post else None

def get_products(ids):
    """Mengambil beberapa produk sekaligus berdasarkan ID"""
    ids = list(ids)
    if not ids:
        return {}
    return {p.pk: to_product(p)for p in api_posts().filter(pk__in=ids)}

def recommended_products(exclude_ids=(), limit=5):
    """Mengambil produk rekomendasi yang belum ada di keranjang"""
    exclude_ids = list(exclude_ids)
    picked = list(api_posts().exclude(pk__in=exclude_ids).order_by("?")[:limit])

    if len(picked) < limit:
        have = [p.pk for p in picked]
        picked += list(api_posts().exclude(pk__in=have).order_by("?")[: limit - len(picked)])
    return [to_product(p) for p in picked]