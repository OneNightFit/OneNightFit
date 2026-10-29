"""
Menyimpan isi keranjang (Cart) user ke database.

Keranjang hanya tersedia untuk authenticated user.
Browser mengirim ID dan detail produk diambil dari catalog.
"""
from django.db import transaction

from .models import Cart, CartItem, Rental

def _get_cart(user):
    result = Cart.objects.get_or_create(user=user)
    cart = result[0]
    return cart

def load_state(user):
    cart = _get_cart(user)
    return {
        "items": [
            {"id": r.post_id, "days": r.days, "selected": r.selected}
            for r in cart.items.all()
        ]
    }

def save_state(user, state):
    """Menyamakan tabel CartItem dengan state"""
    cart = _get_cart(user)
    wanted = {}
    for item in state["items"]:
        wanted[item["id"]] = item

    with transaction.atomic(): 
        cart_items = cart.items.all() # hapus barang yang tidak ada dalam state
        for row in cart_items:
            if row.post_id not in wanted:
                row.delete()

        existing = {} # ambil barang yang masih tersimpan di db
        for row in cart.items.all():
            existing[row.post_id] = row

        for pid in wanted: # tambah atau perbarui barang
            item = wanted[pid]
            if pid not in existing:
                CartItem.objects.create(
                    cart = cart,
                    post_id = pid,
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
    """Menyimpan item yang sudah dibayar sebagai riwayat sewa."""
    Rental.objects.bulk_create([
        Rental(
            buyer=user,
            product_id=i["id"],
            product_name=i["name"],
            image=i["image"] or "",
            store_slug=g["slug"],
            store_name=g["name"],
            price_per_day=i["price"],
            days=i["days"],
            total=i["subtotal"],
        )
        for g in summary["stores"] for i in g["items"]
    ])
