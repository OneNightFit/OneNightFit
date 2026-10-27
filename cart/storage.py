"""
Menyimpan data keranjang. Asumsi jika belum login tetap bisa melakukan transaksi untuk sekadar ngecek fungsionalitas fitur. Akan di ubah ketika fitur autentikasi sudah diimplementasikan.

Authenticated User: menyimpan data di database.
Guest: Menyimpan data di session browser dan ter reset tiap reload.
"""
from django.db import transaction

from . import services
from .models import Cart, CartItem

SESSION_KEY = "onf_cart"
KEEP_ONCE_KEY = "onf_cart_keep_once"

def _rows_to_state(cart):
    return {"items": [{"id": r.post_id, "days": r.days, "selected": r.selected}
                      for r in cart.items.all()]}

def _sync(cart, state):
    """Menyamakan isi keranjang dengan data di database."""
    wanted = {it["id"]: it for it in state["items"]}
    with transaction.atomic():
        cart.items.exclude(post_id__in=list(wanted)).delete()
        existing = {r.post_id: r for r in cart.items.all()}
        for pid, it in wanted.items():
            row = existing.get(pid)
            if row is None:
                CartItem.objects.create(cart=cart, post_id=pid, days=it["days"], selected=it["selected"])
            elif (row.days, row.selected) != (it["days"], it["selected"]):
                row.days, row.selected = it["days"], it["selected"]
                row.save(update_fields=["days", "selected"])

def _account_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    if not cart.seeded:
        initial = services.default_state()
        if initial["items"]:# Coba lagi nanti jika produk belum tersedia
            _sync(cart, initial)
            cart.seeded = True
            cart.save(update_fields=["seeded"])
    return cart

def load_state(request):
    if request.user.is_authenticated:
        return _rows_to_state(_account_cart(request.user))
    state = request.session.get(SESSION_KEY)
    if not services.is_valid_state(state):
        state = services.default_state()
        request.session[SESSION_KEY] = state
    return state

def save_state(request, state):
    if request.user.is_authenticated:
        _sync(_account_cart(request.user), state)
    else:
        request.session[SESSION_KEY] = state
        request.session.modified = True

def keep_guest_cart_once(request):
    """Menjaga isi keranjang Guest setelah checkout berhasil untuk satu kali kunjungan."""
    request.session[KEEP_ONCE_KEY] = True

def reset_guest_cart(request):
    if request.session.pop(KEEP_ONCE_KEY, False):
        return
    request.session[SESSION_KEY] = services.default_state()
    request.session.modified = True