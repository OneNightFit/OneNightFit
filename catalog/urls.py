"""
URL configuration for OneNightFit project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from OneNightFit.views import landing_page
from django.conf import settings
from django.conf.urls.static import static

# catalog/urls.py

from django.urls import path
from catalog import views

app_name = 'catalog'

urlpatterns = [
    # Catalog view / list all products
    path('', views.catalog_list, name='catalog_list'),
    path('add-to-cart/<uuid:id>/', views.add_to_cart, name='add_to_cart'),

    # Detail view for a specific product
    path('<uuid:id>/', views.product_detail, name='product_detail'),
    
    path('json/', views.get_products_json, name='get_products_json'),
    path('create-ajax/', views.create_product_ajax, name='create_product_ajax'),
    path('edit-ajax/<uuid:id>/', views.edit_product_ajax, name='edit_product_ajax'),
    path('delete-ajax/<uuid:id>/', views.delete_product_ajax, name='delete_product_ajax'),
    
    # Toggle wishlist status
    path('wishlist/toggle/<uuid:id>/', views.toggle_wishlist, name='toggle_wishlist'),
    
    # Add to cart
    path('cart/add/<uuid:id>/', views.add_to_cart, name='add_to_cart'),
]
