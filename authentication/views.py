from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .decorators import buyer_required, seller_required
from .forms import DeleteAccountForm, EditProfileForm, LoginForm, SignUpForm
from .reports import get_seller_report


def _safe_next_url(request):
    """Pakai ?next= hanya jika menuju host sendiri (cegah open redirect)."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return None


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
    # Seller mendapat ringkasan laporan toko di bagian atas profil
    report = get_seller_report(request.user) if request.user.profile.is_seller else None
    return render(request, "authentication/profile.html", {"report": report})


@buyer_required
def activity_view(request):
    return render(
        request,
        "authentication/activity.html",
    )


@buyer_required
def rentals_view(request):
    rentals = []
    return render(request, "authentication/rentals.html", {"rentals": rentals})


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
