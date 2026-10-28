from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import catalog, services, storage

# =======================================================
# HELPER
# =======================================================
def _wants_json(request):
    return (request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", ""))

def cart_login_required(view):
    """Meminta login jika CART_REQUIRE_LOGIN aktif.
    Default (sementara) Guest bisa mengakses Cart dengan isi ter reset tiap reload."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if getattr(settings, "CART_REQUIRE_LOGIN", False) and not request.user.is_authenticated:
            if _wants_json(request):
                return JsonResponse({"ok": False, "error": "Silakan login terlebih dahulu."}, status=401)
            return redirect_to_login(request.get_full_path())
        return view(request, *args, **kwargs)
    return wrapper

def recommendations(state):
    recs = catalog.recommended_products(exclude_ids=[it["id"] for it in state["items"]], limit=5)
    return [{**p, "price_display": services.format_rupiah(p["price"])} for p in recs]

def mutate(request, fn):
    """Mengubah isi keranjang dan mengirim respons sesuai request."""
    state = storage.load_state(request)
    try:
        fn(state)
    except services.CartError as exc:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        messages.error(request, str(exc))
        return redirect("cart:cart")
    storage.save_state(request, state)

    if _wants_json(request):
        return JsonResponse({"ok": True, "cart": services.build_cart(state)})
    return redirect("cart:cart")

# =======================================================
# CART PAGE
# =======================================================
@cart_login_required
def cart_page(request):
    if not request.user.is_authenticated:
        storage.reset_guest_cart(request)   # untuk Guest barang kembali muncul setelah reload
    state = storage.load_state(request)
    return render(request, "cart/cart.html", {
        "cart": services.build_cart(state),
        "catalog_empty": not catalog.has_products(),
        "min_days": services.MIN_DAYS,
        "max_days": services.MAX_DAYS,
        "recommendations": recommendations(state),
    })

@cart_login_required
@require_POST
def cart_select(request):
    """Memilih produk atau toko."""
    selected = request.POST.get("selected", "")
    if "store" in request.POST:
        return mutate(request, lambda s: services.set_store_selected(s, request.POST["store"], selected))
    
    return mutate(request, lambda s: services.set_selected(s, request.POST.get("product_id"), selected))


@cart_login_required
@require_POST
def cart_duration(request):
    """Mengubah durasi sewa produk."""
    def run(state):
        pid = services.parse_product_id(request.POST.get("product_id"))
        
        if "days" in request.POST:
            services.set_days(state, pid, request.POST["days"])
            return
        try:
            delta = int(request.POST.get("delta", ""))
        except ValueError:
            raise services.CartError("Perubahan durasi tidak valid.")
        current = next((i["days"] for i in state["items"] if i["id"] == pid), None)
        
        if current is None:
            raise services.CartError("Produk tidak ada di keranjang.")
        services.set_days(state, pid, current + delta)
    return mutate(request, run)


@cart_login_required
@require_POST
def cart_remove(request):
    """Menghapus produk dari keranjang."""
    return mutate(request, lambda s: services.remove_item(s, request.POST.get("product_id")))


@cart_login_required
@require_POST
def cart_add(request):
    """Menambahkan produk ke keranjang dari catalog (belum diimplementasikan)."""
    return mutate(request, lambda s: services.add_item(s, request.POST.get("product_id"), request.POST.get("days", 1), True))


@cart_login_required
@require_POST
def cart_reset(request):
    """Mengembalikan isi keranjang ke kondisi awal."""
    storage.save_state(request, services.default_state())
    return redirect("cart:cart")

# =======================================================
# CHECKOUT PAGE
# =======================================================
@cart_login_required
def checkout_page(request):
    state = storage.load_state(request)
    summary = services.checkout_summary(state)
    ctx = {
        "summary": summary,
        "user_info": {
            "name": (request.user.get_full_name() or request.user.get_username())
                    if request.user.is_authenticated else "John Doe",
            "phone": "+62 812-3443-7700",   # DUMMY (Ganti ketika profil sudah diimplementasi)
            "address": ("Jl. Prof. Dr. Sudjono D. Pusponegoro, Kampus UI, Pondok Cina, "
                        "Kecamatan Beji, Kota Depok, Jawa Barat, 16424"),
        },
        "errors": [],
        "shipping": {g["slug"]: "" for g in summary["stores"]},
        "payment": "",
    }
    if request.method == "POST":
        shipping = {g["slug"]: request.POST.get(f"shipping_{g['slug']}", "")
                    for g in summary["stores"]}
        payment = request.POST.get("payment", "")
        errors = services.validate_checkout(summary, shipping, payment)
        if not errors:
            # Item yang dibayar dihapus dari keranjang.
            services.complete_checkout(state, summary)
            storage.save_state(request, state)
            if not request.user.is_authenticated:
                storage.keep_guest_cart_once(request)     # Guest barang balik setelah reload
            messages.success(request, "Payment Successful.")
            return redirect("cart:cart")
        ctx.update(shipping=shipping, payment=payment, errors=errors)
    return render(request, "cart/checkout.html", ctx)