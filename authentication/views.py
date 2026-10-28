from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignUpForm
from .models import ActivityHistory
from .utils import log_activity


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
        return redirect("landing_page")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_activity(request, user, ActivityHistory.Action.REGISTER, "Account created.")
        login(request, user)
        messages.success(request, f"Welcome to OneNightFit, {user.first_name}!")
        return redirect("landing_page")
    return render(request, "authentication/signup.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("landing_page")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        log_activity(request, user, ActivityHistory.Action.LOGIN, "Logged in.")
        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
        return redirect(_safe_next_url(request) or "landing_page")

    return render(
        request,
        "authentication/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )
    
@require_POST
@login_required
def logout_view(request):
    log_activity(request, request.user, ActivityHistory.Action.LOGOUT, "Logged out.")
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("authentication:login")


