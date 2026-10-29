from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import catalog, services, storage
from .models import Rental, local_rental_date

# =======================================================
# HELPER
# =======================================================
def _wants_json(request):
    return (request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", ""))

def cart_login_required(view):
    """Cart hanya untuk pengguna yang bukan seller."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if _wants_json(request):
                return JsonResponse({"ok": False, "error": "Please log in first."}, status=401)
            return redirect_to_login(request.get_full_path())
        if getattr(getattr(request.user, "profile", None), "is_seller", False):
            if _wants_json(request):
                return JsonResponse({"ok": False, "error": "Cart is not available to sellers."}, status=403)
            return redirect("catalog:catalog_list")
        return view(request, *args, **kwargs)
    return wrapper

def recommendations(state):
    recs = catalog.recommended_products(
        exclude_ids=[item["id"] for item in state["items"]],
        limit=5,
    )
    return [
        {**product, "price_display": services.format_rupiah(product["price"])}
        for product in recs
    ]

def mutate(request, fn):
    """Mengubah isi keranjang dan mengirim respons sesuai request."""
    state = storage.load_state(request.user)
    try:
        fn(state)
    except services.CartError as exc:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        messages.error(request, str(exc))
        return redirect("cart:cart")
    storage.save_state(request.user, state)

    if _wants_json(request):
        return JsonResponse({"ok": True, "cart": services.build_cart(state)})
    return redirect("cart:cart")

# =======================================================
# CART PAGE
# =======================================================
@cart_login_required
def cart_page(request):
    state = storage.load_state(request.user)
    return render(request, "cart/cart.html", {
        "cart": services.build_cart(state),
        "min_days": services.MIN_DAYS,
        "max_days": services.MAX_DAYS,
        "recommendations": recommendations(state),
    })

@cart_login_required
@require_POST
def cart_select(request):
    """Memilih produk atau satu toko sekaligus."""
    selected = request.POST.get("selected", "")
    if "store" in request.POST:
        def update_store_selection(state):
            return services.set_store_selected(
                state,
                request.POST["store"],
                selected
            )
        return mutate(request, update_store_selection)
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
            raise services.CartError("The selected duration is invalid.")
        
        current = next((i["days"] for i in state["items"] if i["id"] == pid), None)

        if current is None:
            raise services.CartError("Your cart is empty.")
        services.set_days(state, pid, current + delta)
    return mutate(request, run)


@cart_login_required
@require_POST
def cart_remove(request):
    """Menghapus produk dari keranjang."""
    product_id = request.POST.get("product_id")
    def remove(state):
        return services.remove_item(state, product_id)
    return mutate(request, remove)


@cart_login_required
@require_POST
def cart_add(request):
    """Menambahkan produk ke keranjang dari catalog lewat 'Add to Cart'."""
    def add(state):
        product_id = request.POST.get("product_id")
        days = request.POST.get("days", 1)
        return services.add_item(state, product_id, days, False)
    return mutate(request, add)

# =======================================================
# CHECKOUT PAGE
# =======================================================
@cart_login_required
def checkout_page(request):
    state = storage.load_state(request.user)
    summary = services.checkout_summary(state)
    ctx = {
        "summary": summary,
        "user_info": {
            "name": (request.user.get_full_name() or request.user.get_username()),
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
            try:
                with transaction.atomic():
                    product_ids = [item["id"] for store in summary["stores"] for item in store["items"]]
                    if Rental.objects.filter(
                        product_uuid__in=product_ids,
                        rental_date=local_rental_date(),
                    ).exists():
                        raise services.CartError("A product in this cart was just rented by someone else.")
                    services.complete_checkout(state, summary)
                    storage.save_state(request.user, state)
                    storage.record_rentals(request.user, summary)
            except (IntegrityError, services.CartError):
                ctx.update(
                    errors=["A product in this cart was just rented by someone else. Please review your cart."],
                    shipping=shipping,
                    payment=payment,
                )
                return render(request, "cart/checkout.html", ctx)
            messages.success(request, "Your rental is confirmed!")
            return redirect("landing_page")
        ctx.update(shipping=shipping, payment=payment, errors=errors)
    return render(request, "cart/checkout.html", ctx)
