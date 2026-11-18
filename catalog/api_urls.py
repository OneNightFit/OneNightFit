from django.urls import path

from catalog import api_views

app_name = "api"

urlpatterns = [
    path("products/", api_views.product_list, name="product-list"),
    path("products/<uuid:product_id>/", api_views.product_detail, name="product-detail"),
    path(
        "products/<uuid:product_id>/wishlist/",
        api_views.product_wishlist,
        name="product-wishlist",
    ),
]
