"""Mengatur isi  (Cart). Data produk diambil dari catalog.

Keranjang hanya menyimpan ID produk, lama sewa, dan status pilihan.
Nama, harga, dan ketersediaan produk selalu diambil ulang dari catalog
agar data tetap sesuai dan tidak bergantung pada data dari browser.
"""

from . import catalog

MIN_DAYS = 1
MAX_DAYS = 30
DEFAULT_CART_SIZE = 4

class CartError(ValueError):
    """Error yang digunakan saat input keranjang tidak valid."""

def format_rupiah(amount):
    return "Rp" + f"{int(amount):,}".replace(",", ".")

# =======================================================
# PARSING
# =======================================================
def parse_product_id(raw):
    try:
        pid = int(str(raw).strip())
    except (TypeError, ValueError):
        raise CartError("Produk tidak valid.")
    if pid < 1:
        raise CartError("Produk tidak valid.")
    return pid

def parse_days(raw):
    try:
        days = int(str(raw).strip())
    except (TypeError, ValueError):
        raise CartError("Durasi sewa harus berupa angka.")
    if days < MIN_DAYS:
        raise CartError(f"Durasi sewa minimal {MIN_DAYS} hari.")
    if days > MAX_DAYS:
        raise CartError(f"Durasi sewa maksimal {MAX_DAYS} hari.")
    return days

def parse_bool(raw):
    value = str(raw).strip().lower()
    if value in ("1", "true", "on", "yes"):
        return True
    if value in ("0", "false", "off", "no", ""):
        return False
    raise CartError("Nilai pilihan tidak valid.")

# =======================================================
# STATE
# =======================================================
def new_state():
    return {"items": []}

def default_state():
    """Mengisi keranjang awal dengan produk contoh."""
    state = new_state()
    for i, p in enumerate(catalog.default_cart_products(DEFAULT_CART_SIZE)):
        state["items"].append({"id": p["id"], "days": 2 if i == 1 else 1, "selected": i < 2})
    return state

def is_valid_state(state):
    if not isinstance(state, dict) or not isinstance(state.get("items"), list):
        return False
    for it in state["items"]:
        if not (isinstance(it, dict) and isinstance(it.get("id"), int)
                and isinstance(it.get("days"), int) and isinstance(it.get("selected"), bool)):
            return False
    return True

def _find(state, pid):
    for it in state["items"]:
        if it["id"] == pid:
            return it
    return None

def _require_in_cart(state, pid):
    item = _find(state, pid)
    if item is None:
        raise CartError("Produk tidak ada di keranjang.")
    return item

def add_item(state, product_id, days=1, selected=True):
    pid = parse_product_id(product_id)
    days = parse_days(days)
    product = catalog.get_product(pid)
    if product is None:
        raise CartError("Produk tidak ditemukan.")
    if not product["available"]:
        raise CartError("Produk ini sedang tidak tersedia.")
    existing = _find(state, pid)
    if existing:                     
        existing["days"] = days
        existing["selected"] = bool(selected)
    else:
        state["items"].append({"id": pid, "days": days, "selected": bool(selected)})
    return state

def remove_item(state, product_id):
    pid = parse_product_id(product_id)
    _require_in_cart(state, pid)
    state["items"] = [it for it in state["items"] if it["id"] != pid]
    return state

def set_days(state, product_id, days):
    pid = parse_product_id(product_id)
    item = _require_in_cart(state, pid)
    item["days"] = parse_days(days)
    return state

def set_selected(state, product_id, selected):
    pid = parse_product_id(product_id)
    item = _require_in_cart(state, pid)
    selected = parse_bool(selected)
    if selected:
        product = catalog.get_product(pid)
        if product is None or not product["available"]:
            raise CartError("Produk ini sedang tidak tersedia.")
    item["selected"] = selected
    return state

def set_store_selected(state, store_slug, selected):
    selected = parse_bool(selected)
    products = catalog.get_products([it["id"] for it in state["items"]])
    targets = [it for it in state["items"]
               if products.get(it["id"]) and products[it["id"]]["store"] == store_slug]
    if not targets:
        raise CartError("Toko tidak ditemukan di keranjang.")
    for it in targets:
        it["selected"] = selected and products[it["id"]]["available"]
    return state

# =======================================================
# CALCULATION
# =======================================================
def build_cart(state):
    """Menyiapkan data Cart dan menghitung total belanja."""
    products = catalog.get_products([it["id"] for it in state["items"]])
    stores = {}
    total = 0
    selected_count = 0
    for it in state["items"]:
        p = products.get(it["id"])
        if p is None:
            continue
        days = min(max(it["days"], MIN_DAYS), MAX_DAYS)
        selected = bool(it["selected"]) and p["available"]
        subtotal = p["price"] * days
        if selected:
            total += subtotal
            selected_count += 1
        group = stores.setdefault(p["store"], {
            "slug": p["store"], "name": p["store_name"], "items": []})
        group["items"].append({
            "id": p["id"], "name": p["name"], "image": p["image"], "size": p["size"],
            "available": p["available"], "selected": selected, "days": days,
            "price": p["price"], "price_display": format_rupiah(p["price"]),
            "subtotal": subtotal, "subtotal_display": format_rupiah(subtotal),
            "store_slug": p["store"], "store_name": p["store_name"],
        })
    store_list = list(stores.values())
    for g in store_list:
        n_sel = sum(1 for i in g["items"] if i["selected"])
        selectable = sum(1 for i in g["items"] if i["available"])
        g["all_selected"] = selectable > 0 and n_sel == selectable
        g["some_selected"] = 0 < n_sel < selectable
    return {
        "stores": store_list,
        "total": total,
        "total_display": format_rupiah(total),
        "selected_count": selected_count,
        "item_count": sum(len(g["items"]) for g in store_list),
        "can_checkout": selected_count > 0,
    }

def checkout_summary(state):
    """Mengambil produk terpilih dan total harga untuk checkout."""
    cart = build_cart(state)
    stores = []
    for g in cart["stores"]:
        items = [i for i in g["items"] if i["selected"]]
        if items:
            stores.append({"slug": g["slug"], "name": g["name"], "items": items})
    return {"stores": stores, "total": cart["total"], "total_display": cart["total_display"],
            "selected_count": cart["selected_count"], "is_empty": cart["selected_count"] == 0}

# =======================================================
# CHECKOUT
# =======================================================
SHIPPING_OPTIONS = ("pickup", "delivery")
PAYMENT_METHODS = ("qris", "tunai")

def validate_checkout(summary, shipping_by_store, payment):
    """Mengecek apakah semua pilihan checkout sudah diisi."""
    if summary["is_empty"]:
        return ["Belum ada produk yang dipilih untuk checkout."]
    errors = []
    for g in summary["stores"]:
        if shipping_by_store.get(g["slug"]) not in SHIPPING_OPTIONS:
            errors.append(f"Pilih opsi pengiriman untuk toko {g['name']}.")
    if payment not in PAYMENT_METHODS:
        errors.append("Pilih metode pembayaran.")
    return errors

def complete_checkout(state, summary):
    """Menghapus produk yang sudah selesai di-checkout dari keranjang."""
    paid_ids = {i["id"] for g in summary["stores"] for i in g["items"]}
    state["items"] = [it for it in state["items"] if it["id"] not in paid_ids]
    return state