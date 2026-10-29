from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from catalog.models import Product
from catalog.forms import ProductForm
from django.contrib import messages
from django.core.exceptions import PermissionDenied
import requests
import random
from django.db.models import Q
from django.http import JsonResponse
from cart.models import CartItem

def landing_page(request):
    return render(request, "index.html")

def is_seller(user):
    # Helper untuk memvalidasi apakah user memiliki role seller
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_seller


def product_detail(request, id):
    product = get_object_or_404(Product.objects.select_related('seller'), id=id)
    is_wishlisted = (
        request.user.is_authenticated
        and product.wishlisted_by.filter(pk=request.user.pk).exists()
    )
    return JsonResponse({
        "pk": str(product.id),
        "fields": {
            "name": product.name,
            "description": product.description,
            "image": product.image_src,
            "price": str(product.price),
            "category": product.category,
            "category_display": product.get_category_display(),
            "size": product.size,
            "size_display": product.get_size_display(),
            "seller": product.seller.username if product.seller else "-",
            "average_rating": product.average_rating,
            "rating_count": product.rating_count,
            "is_wishlisted": is_wishlisted,
            "is_owner": request.user.is_authenticated and product.seller_id == request.user.id,
        }
    })


def catalog_list(request):
    """Render halaman katalog. Data produk diambil lewat get_products_json."""
    selected_categories = request.GET.getlist('category')
    base_products = Product.objects.all()

    if is_seller(request.user):
        base_products = base_products.filter(seller=request.user)

    categories_data = [
        (code, name, base_products.filter(category=code).count())
        for code, name in Product.PRODUCT_CATEGORY
    ]
    context = {
        'categories': categories_data,
        'category_choices': Product.PRODUCT_CATEGORY,
        'selected_categories': selected_categories,
        'search_query': request.GET.get('q', '').strip(),
        'form': ProductForm(),
        'update_form': ProductForm(auto_id='update_%s'),
    }

    return render(request, 'catalog/catalog.html', context)


def get_products_json(request):
    selected_categories = request.GET.getlist('category')
    search_query = request.GET.get('q', '').strip()
    products = Product.objects.select_related('seller').prefetch_related('wishlisted_by', 'ratings')

    if is_seller(request.user):
        products = products.filter(seller=request.user)
    if selected_categories:
        products = products.filter(category__in=selected_categories)
    if search_query:
        products = products.filter(name__icontains=search_query)

    cart_product_ids = set()
    if request.user.is_authenticated:
        cart_product_ids = set(
            CartItem.objects.filter(
                cart__user=request.user,
                product__isnull=False,
            ).values_list('product_id', flat=True)
        )

    data = []
    for product in products:
        wishlisted_users = product.wishlisted_by.all()
        is_wishlisted = request.user.is_authenticated and request.user in wishlisted_users

        data.append({
            "pk": str(product.id),
            "fields": {
                "name": product.name,
                "description": product.description,
                "image": product.image_src,
                "image_url": product.image or "",
                "image_is_upload": bool(product.image_file),
                "price": str(product.price),
                "category": product.category,
                "category_display": product.get_category_display(),
                "size": product.size,
                "size_display": product.get_size_display(),
                "seller": product.seller.username if product.seller else "-",
                "average_rating": product.average_rating,
                "rating_count": product.rating_count,
                "is_wishlisted": is_wishlisted,
                "is_in_cart": product.id in cart_product_ids,
                "is_owner": request.user.is_authenticated and product.seller_id == request.user.id,
            }
        })

    return JsonResponse(data, safe=False)


@require_POST
def create_product_ajax(request):
    if not is_seller(request.user):
        return JsonResponse({"message": "Hanya seller yang dapat menambahkan produk."}, status=403)

    # Added request.FILES to handle image uploads
    form = ProductForm(request.POST, request.FILES) 
    if form.is_valid():
        product = form.save(commit=False)
        product.seller = request.user
        product.save()
        return JsonResponse({"message": "Produk berhasil ditambahkan.", "pk": str(product.id)}, status=201)
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def edit_product_ajax(request, id):
    product = get_object_or_404(Product, pk=id)
    if not is_seller(request.user) or product.seller != request.user:
        return JsonResponse({"message": "Anda tidak berhak mengedit produk ini."}, status=403)

    # Added request.FILES to handle image uploads
    form = ProductForm(request.POST, request.FILES, instance=product) 
    if form.is_valid():
        form.save()
        return JsonResponse({"message": "Produk berhasil diperbarui.", "pk": str(product.id)})
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def delete_product_ajax(request, id):
    product = get_object_or_404(Product, pk=id)

    if not is_seller(request.user) or product.seller != request.user:
        return JsonResponse(
            {"message": "Anda tidak berhak menghapus produk ini."},
            status=403,
        )

    product.delete()
    return JsonResponse({"message": "Produk berhasil dihapus."})

@require_POST
def toggle_wishlist(request, id):
    if not request.user.is_authenticated:
        message = "Please login to continue."
        messages.info(request, message)
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"message": message}, status=401)
        return redirect("authentication:login")
        
    product = get_object_or_404(Product, id=id)
    if request.user in product.wishlisted_by.all():
        product.wishlisted_by.remove(request.user)
        is_wishlisted = False
    else:
        product.wishlisted_by.add(request.user)
        is_wishlisted = True
        
    return JsonResponse({
        "message": "Wishlist berhasil diperbarui.",
        "is_wishlisted": is_wishlisted
    })

@require_POST
def add_to_cart(request, id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Harap login terlebih dahulu."}, status=401)
        
    product = get_object_or_404(Product, id=id)
    cart = request.session.get('cart', {})
    product_id = str(product.id)
    
    if product_id in cart:
        cart[product_id]['quantity'] += 1
    else:
        cart[product_id] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1
        }
        
    request.session['cart'] = cart
    request.session.modified = True # Pastikan session tersimpan
    
    return JsonResponse({"message": f'"{product.name}" berhasil ditambahkan ke keranjang!'})
