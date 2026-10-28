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
    
    # 1. Ambil data asli dari database Django
    products = Product.objects.all()
    
    # 2. Hitung jumlah produk per kategori menggunakan metode filter bawaan Django
    categories_data = [
        (code, name, products.filter(category=code).count())
        for code, name in Product.PRODUCT_CATEGORY
    ]

    # 3. Filter produk berdasarkan kategori yang dicentang
    if selected_categories:
        products = products.filter(category__in=selected_categories)

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
        # Tahan commit penyimpanan form untuk memasukkan data seller
        product = form.save(commit=False)
        product.seller = request.user
        product.save()
        
        messages.success(request, "Produk baru berhasil ditambahkan!")
        return redirect("catalog:catalog_list")
        
    context = {"form": form}
    return render(request, "catalog_form_create.html", context)


@require_POST
@login_required(login_url='/login/')
def edit_product(request, product_id):
    catalog = get_object_or_404(Product, pk=product_id)
    
    if not is_seller(request.user) or catalog.seller != request.user:
        raise PermissionDenied
        
    form = ProductForm(request.POST or None, instance=catalog)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produk berhasil diperbarui!")
        return redirect("catalog:catalog_list")
        
    context = {"form": form, "catalog": catalog}
    return render(request, "catalog_form_update.html", context)


@require_POST
@login_required(login_url='/login/')
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    
    if not is_seller(request.user) or product.seller != request.user:
        raise PermissionDenied
        
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