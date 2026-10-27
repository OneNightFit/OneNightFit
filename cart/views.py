from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render

from . import catalog, services, storage

# =======================================================
# HELPER
# =======================================================
def _wants_json(request):
    return (request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", ""))

def cart_login_required(view):
    """Meminta login jika CART_REQUIRE_LOGIN aktif.
    Default (sementara) Guest bisa mengakses Cart dengan isi ter reset tiap reload"""
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

# =======================================================
# CART PAGE
# =======================================================
@cart_login_required
def cart_page(request):
    if not request.user.is_authenticated:
        storage.reset_guest_cart(request)      # untuk Guest barang kembali muncul setelah reload
    state = storage.load_state(request)
    return render(request, "cart/cart.html", {
        "cart": services.build_cart(state),
        "catalog_empty": not catalog.has_products(),
        "min_days": services.MIN_DAYS,
        "max_days": services.MAX_DAYS,
        "recommendations": recommendations(state),
    })

# =======================================================
# CHECKOUT PAGE
# =======================================================
@cart_login_required
def checkout_page(request):
    return render(request, "cart/checkout.html")