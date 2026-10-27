from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_page, name = "cart"),
    path("checkout/", views.checkout_page, name = "checkout"),
]