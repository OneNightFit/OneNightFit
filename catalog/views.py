from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from catalog.models import Product
from catalog.forms import ProductForm
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import requests
import random


def landing_page(request):
    return render(request, "index.html")

def is_seller(user):
    # Helper untuk memvalidasi apakah user memiliki role seller
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_seller


def catalog_list(request):
    """Displays all products in the catalog."""
    selected_categories = request.GET.getlist('category')
    try:
        res = requests.get("https://fakestoreapi.com/products", timeout=10)
        res.raise_for_status()
        api_data = res.json()
    except (requests.RequestException, ValueError):
        api_data = []

    products = []
    
    # Mapping untuk mencocokkan kategori API dengan kode kategori di Models Anda
    category_mapping = {
        "electronics": "electronics",
        "jewelery": "jewelery",
        "men's clothing": "men_clothing",
        "women's clothing": "women_clothing"
    }
    
    # Mapping untuk menerjemahkan singkatan size menjadi teks penuh (display)
    size_choices = {'S': 'Small', 'M': 'Medium', 'L': 'Large', 'XL': 'Extra Large'}
    
    # 2. Normalisasi data API ke format variabel template katalog
    for item in api_data:
        api_cat = item.get("category", "")
        mapped_code = category_mapping.get(api_cat, "men_clothing")
        
        # Generate size acak
        random_size_key = random.choice(list(size_choices.keys()))
        random_size_display = size_choices[random_size_key]

        products.append({
            "id": item["id"],
            "image": item["image"],
            "category_code": mapped_code, # untuk count dan filter
            "get_category_display": item["category"].title(), 
            "price": item["price"],
            "name": item["title"], 
            "description": item["description"],
            "average_rating": item["rating"]["rate"] if "rating" in item else 0,
            "rating_count": item["rating"]["count"] if "rating" in item else 0,
            "get_size_display": random_size_display, # <-- Ditambahkan agar size muncul di HTML
        })

    # Hitung jumlah produk per kategori
    categories_data = []
    for code, name in Product.PRODUCT_CATEGORY:
        count = len([p for p in products if p.get('category_code') == code]) 
        categories_data.append((code, name, count))

    # Filter produk berdasarkan kategori yang dicentang
    if selected_categories:
        products = [p for p in products if p.get('category_code') in selected_categories]

    context = {
        'products': products,
        'categories': categories_data,
        'category_choices': Product.PRODUCT_CATEGORY, 
        'selected_categories': selected_categories,
        'form': ProductForm(), 
    }
    return render(request, 'catalog/catalog.html', context)

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'catalog/product_detail.html', {'product': product})

# CRUD
@require_POST
@login_required(login_url='/login/')
def create_product(request):
    if not is_seller(request.user):
        return redirect('catalog:catalog_list')
        
    form = ProductForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Skill baru berhasil ditambahkan!")
        return redirect("catalog:catalog_list")

    context = {
        "form": form,
    }
    return render(request, "catalog_form_create.html", context)

@require_POST
@login_required(login_url='/login/')
def edit_product(request, product_id):
    catalog = get_object_or_404(Product, pk=product_id)
    form = ProductForm(request.POST or None, instance=catalog)

    if not is_seller(request.user):
            raise PermissionDenied
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produk berhasil diperbarui!")
        return redirect("catalog:catalog_list")

    context = {
        "form": form,
        "catalog": catalog,
    }
    return render(request, "catalog_form_update.html", context)

@require_POST
@login_required(login_url='/login/')
def delete_product(request, id):
    if not is_seller(request.user):
        return redirect('catalog:catalog_list')
        
    product = get_object_or_404(Product, id=id)
    product.delete()
    return redirect('catalog:catalog_list')

@require_POST
@login_required(login_url='/login/')
def toggle_wishlist(request, id):
    product = get_object_or_404(Product, id=id)
    if request.user in product.wishlisted_by.all():
        product.wishlisted_by.remove(request.user)
    else:
        product.wishlisted_by.add(request.user)
    return redirect('catalog:catalog_list')

@login_required(login_url='/login/')
def add_to_cart(request, id):
    # TODO: Implementasi logika Cart
    return redirect('catalog:catalog_list')