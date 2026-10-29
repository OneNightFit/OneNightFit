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
    
    # Ambil data asli dari database Django
    products = Product.objects.all()
    
    # Hitung jumlah produk per kategori menggunakan metode filter bawaan Django
    categories_data = [
        (code, name, products.filter(category=code).count())
        for code, name in Product.PRODUCT_CATEGORY
    ]

    # Jika user adalah seller, filter produk hanya yang dimiliki oleh seller tersebut
    if is_seller(request.user):
        products = list(products)
        for p in products:
            p.edit_form = ProductForm(instance=p, auto_id=f"id_%s_{p.id}")

    # Filter produk berdasarkan kategori yang dicentang
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

    form = ProductForm(request.POST)
    if form.is_valid():
        product = form.save(commit=False)
        product.seller = request.user
        product.save()
        messages.success(request, "Produk baru berhasil ditambahkan!")
    else:
        messages.error(request, "Gagal menambahkan produk, periksa kembali isian form.")
    return redirect("catalog:catalog_list")


@require_POST
@login_required(login_url='/login/')
def edit_product(request, id):
    catalog = get_object_or_404(Product, pk=id)

    if not is_seller(request.user) or catalog.seller != request.user:
        raise PermissionDenied

    form = ProductForm(request.POST, instance=catalog)
    if form.is_valid():
        form.save()
        messages.success(request, "Produk berhasil diperbarui!")
    else:
        messages.error(request, "Gagal memperbarui produk, periksa kembali isian form.")
    return redirect("catalog:catalog_list")


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
    # 1. Dapatkan objek produk, kembalikan 404 jika tidak ditemukan
    product = get_object_or_404(Product, id=id)
    
    # 2. Ambil dictionary keranjang dari session, atau buat baru jika belum ada
    cart = request.session.get('cart', {})
    
    # 3. Ubah UUID menjadi string
    product_id = str(product.id)
    
    # 4. Implementasi logika penambahan barang (tambah kuantitas jika sudah ada)
    if product_id in cart:
        cart[product_id]['quantity'] += 1
    else:
        cart[product_id] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1
        }
        
    # 5. Simpan kembali data keranjang yang sudah diperbarui ke session
    request.session['cart'] = cart
    
    # 6. Berikan notifikasi sukses kepada user
    messages.success(request, f'"{product.name}" berhasil ditambahkan ke keranjang!')
    
    # 7. Redirect kembali ke halaman katalog
    return redirect('catalog:catalog_list')