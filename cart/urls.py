from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_page, name = "cart"),
    path("select/", views.cart_select, name="select"),
    path("duration/", views.cart_duration, name="duration"),
    path("remove/", views.cart_remove, name="remove"),
    path("add/", views.cart_add, name="add"),
    path("reset/", views.cart_reset, name="reset"),
    path("checkout/", views.checkout_page, name = "checkout"),
]