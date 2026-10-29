from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.urls import NoReverseMatch, reverse
from inspo.models import Bookmark
from .decorators import buyer_required, seller_required
from .forms import DeleteAccountForm, EditProfileForm, LoginForm, SignUpForm
from cart.reports import get_seller_report
BOOKMARK_PAGE_URL_NAME = "inspo:bookmark_list" 
from .integrations import (
    buyer_wishlist, product_card, inspo_card,
    inspo_bookmarks, inspo_likes,
    inspo_bookmark_items, inspo_bookmark_categories, inspo_like_items,
)


def _safe_next_url(request):
    """Pakai ?next= hanya jika menuju host sendiri (cegah open redirect)."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return None

def _safe_reverse(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return ""
    
def signup_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to OneNightFit, {user.first_name}!")
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, "authentication/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
        return redirect(_safe_next_url(request) or settings.LOGIN_REDIRECT_URL)

    return render(
        request,
        "authentication/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def profile_view(request):
    report = get_seller_report(request.user) if request.user.profile.is_seller else None
    return render(request, "authentication/profile.html", {"report": report})

@login_required
def activity_view(request):
    user = request.user

    wishlist = []
    if user.profile.is_buyer:
        products = buyer_wishlist(user)
        wishlist = [product_card(p) for p in products.order_by("-pk")] if products is not None else []
    liked = [inspo_card(p) for p in (inspo_likes(user) or [])]
    bookmarked = [inspo_card(p) for p in (inspo_bookmarks(user) or [])]

    tabs = []
    if user.profile.is_buyer:
        tabs.append({
            "key": "wishlist", "label": "Wishlist", "cards": wishlist,
            "heading": ("Wishlist", "Product"),
            "empty": "No wishlist products yet. Tap the heart on a product to save it here.",
        })
    tabs.append({
        "key": "like", "label": "Like", "cards": liked,
        "heading": ("Like", "Inspo"), "empty": "No liked inspo yet.",
    })
    tabs.append({
        "key": "bookmark", "label": "Bookmark", "cards": bookmarked,
        "heading": ("Bookmark", "Inspo"), "empty": "No bookmarked inspo yet.",
        "url": _safe_reverse(BOOKMARK_PAGE_URL_NAME),
    })

    active = next((t for t in tabs if t["key"] == request.GET.get("tab")), tabs[0])
    ctx = {"tabs": tabs, "active": active, "current": active["key"], "wishlist": wishlist}

    if active["key"] == "bookmark":
        sort = request.GET.get("urut", "terbaru")
        if sort not in ("terbaru", "terlama"):
            sort = "terbaru"
        active_category = request.GET.get("kategori", "")

        items = inspo_bookmark_items(user, active_category, sort)
        if items is None:
            items = []
        ctx.update({
            "items": items,
            "total": len(items),
            "categories": inspo_bookmark_categories(user),
            "active_category": active_category,
            "sort": sort,
        })

    if active["key"] == "like":
        liked_items = inspo_like_items(user)
        ctx["liked_items"] = liked_items if liked_items is not None else []

    return render(request, "authentication/activity.html", ctx)

@buyer_required
def rentals_view(request):
    return render(request, "cart/rentals.html", {"rentals": request.user.rentals.all()})

@seller_required
def shop_report_view(request):
    return render(
        request,
        "authentication/shop_report.html",
        {"report": get_seller_report(request.user)},
    )

@login_required
def edit_profile_view(request):
    form = EditProfileForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("authentication:profile")
    return render(request, "authentication/edit_profile.html", {"form": form})

@login_required
def change_password_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # sesi tetap aktif
        messages.success(request, "Your password has been changed.")
        return redirect("authentication:profile")
    return render(request, "authentication/change_password.html", {"form": form})

@login_required
def delete_account_view(request):
    form = DeleteAccountForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()  
        messages.success(request, "Your account has been deleted. See you again!")
        return redirect("authentication:signup")
    return render(request, "authentication/delete_account.html", {"form": form})
