"""
Menyimpan isi keranjang (Cart) user ke database.

Keranjang hanya tersedia untuk authenticated user.
Browser mengirim ID dan detail produk diambil dari catalog.
"""
from django.db import transaction

from .models import Cart, CartItem, Rental, local_rental_date

def _get_cart(user):
    result = Cart.objects.get_or_create(user=user)
    cart = result[0]
    return cart

def load_state(user):
    cart = _get_cart(user)
    return {
        "items": [
            {"id": r.product_id, "days": r.days, "selected": r.selected}
            for r in cart.items.filter(product__isnull=False)
        ]
    }

def save_state(user, state):
    """Menyamakan tabel CartItem dengan state"""
    cart = _get_cart(user)
    wanted = {}
    for item in state["items"]:
        wanted[item["id"]] = item

    with transaction.atomic(): 
        cart_items = cart.items.filter(product__isnull=False)
        for row in cart_items:
            if row.product_id not in wanted:
                row.delete()

        existing = {} # ambil barang yang masih tersimpan di db
        for row in cart.items.filter(product__isnull=False):
            existing[row.product_id] = row

        for pid in wanted: # tambah atau perbarui barang
            item = wanted[pid]
            if pid not in existing:
                CartItem.objects.create(
                    cart = cart,
                    product_id = pid,
                    days = item["days"],
                    selected = item["selected"]
                )
            else: 
                row = existing[pid]
                if (row.days != item["days"] or row.selected != item["selected"]):
                    row.days = item["days"]
                    row.selected = item["selected"]
                    row.save(update_fields = ["days", "selected"])

def record_rentals(user, summary):
    """Catat produk yang dipesan pada tanggal sewa saat ini."""
    rental_date = local_rental_date()
    Rental.objects.bulk_create([
        Rental(
            buyer=user,
            product_id=None,
            product_uuid=item["id"],
            rental_date=rental_date,
            product_name=item["name"],
            image=item["image"] or "",
            store_slug=store["slug"],
            store_name=store["name"],
            price_per_day=item["price"],
            days=item["days"],
            total=item["subtotal"],
        )
        for store in summary["stores"] for item in store["items"]
    ])
