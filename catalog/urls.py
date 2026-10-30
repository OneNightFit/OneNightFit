from django.urls import path
from catalog import views

app_name = 'catalog'

urlpatterns = [
    # Catalog view / list all products
    path('', views.catalog_list, name='catalog_list'),

    # Detail view for a specific product
    path('<uuid:id>/', views.product_detail, name='product_detail'),

    # Products JSON data endpoint
    path('json/', views.get_products_json, name='get_products_json'),

    # AJAX CRUD endpoints
    path('create-ajax/', views.create_product_ajax, name='create_product_ajax'),
    path('edit-ajax/<uuid:id>/', views.edit_product_ajax, name='edit_product_ajax'),
    path('delete-ajax/<uuid:id>/', views.delete_product_ajax, name='delete_product_ajax'),

    # Backwards-compatible aliases for CRUD endpoints
    path('create/', views.create_product_ajax, name='create_product'),
    path('edit/<uuid:id>/', views.edit_product_ajax, name='edit_product'),
    path('delete/<uuid:id>/', views.delete_product_ajax, name='delete_product'),

    # Wishlist toggle endpoint
    path('wishlist/toggle/<uuid:id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # Add to cart endpoints
    path('add-to-cart/<uuid:id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add/<uuid:id>/', views.add_to_cart, name='add_to_cart_alias'),
]
