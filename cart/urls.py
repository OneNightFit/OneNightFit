from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("cart/", views.cart_page, name = "cart"),
    path("cart/select/", views.cart_select, name="select"),
    path("cart/duration/", views.cart_duration, name="duration"),
    path("cart/remove/", views.cart_remove, name="remove"),
    path("cart/add/", views.cart_add, name="add"),
    path("cart/checkout/", views.checkout_page, name = "checkout"),
]