from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse

from catalog.models import Product
from catalog.forms import ProductForm
from cart.catalog import unavailable_product_ids
from cart.models import CartItem


def is_seller(user):
    """Helper untuk memvalidasi apakah user memiliki role seller."""
    return user.is_authenticated and getattr(getattr(user, 'profile', None), 'is_seller', False)


def serialize_product(product, user=None, wishlisted_ids=None, cart_product_ids=None):
    """Serialisasi data produk ke dictionary standar JSON."""
    if user and user.is_authenticated:
        if wishlisted_ids is not None:
            is_wishlisted = product.id in wishlisted_ids
        else:
            is_wishlisted = product.wishlisted_by.filter(pk=user.pk).exists()

        if cart_product_ids is not None:
            is_in_cart = product.id in cart_product_ids
        else:
            is_in_cart = CartItem.objects.filter(cart__user=user, product=product).exists()

        is_owner = product.seller_id == user.id
    else:
        is_wishlisted = False
        is_in_cart = False
        is_owner = False

    return {
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
            "seller_display": product.seller_display,
            "average_rating": product.average_rating,
            "rating_count": product.rating_count,
            "is_wishlisted": is_wishlisted,
            "is_in_cart": is_in_cart,
            "is_owner": is_owner,
        }
    }


def product_detail(request, id):
    product = get_object_or_404(
        Product.objects.select_related('seller', 'seller__profile').annotate(
            avg_score=Avg('ratings__score'),
            ratings_cnt=Count('ratings', distinct=True)
        ),
        id=id
    )
    return JsonResponse(serialize_product(product, user=request.user))


def catalog_list(request):
    """Render halaman katalog. Data produk diambil secara asinkron lewat get_products_json."""
    selected_categories = request.GET.getlist('category')
    base_products = Product.objects.all()

    if is_seller(request.user):
        base_products = base_products.filter(seller=request.user)

    counts = dict(
        base_products.values('category')
        .annotate(c=Count('id'))
        .values_list('category', 'c')
    )
    categories_data = [
        (code, name, counts.get(code, 0))
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

    products = (
        Product.objects.select_related('seller', 'seller__profile')
        .annotate(
            avg_score=Avg('ratings__score'),
            ratings_cnt=Count('ratings', distinct=True)
        )
        .exclude(pk__in=unavailable_product_ids())
    )

    if is_seller(request.user):
        products = products.filter(seller=request.user)
    if selected_categories:
        products = products.filter(category__in=selected_categories)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

    cart_product_ids = set()
    wishlisted_ids = set()
    if request.user.is_authenticated:
        cart_product_ids = set(
            CartItem.objects.filter(
                cart__user=request.user,
                product__isnull=False,
            ).values_list('product_id', flat=True)
        )
        wishlisted_ids = set(
            request.user.wishlisted_product.values_list('id', flat=True)
        )

    data = [
        serialize_product(
            product,
            user=request.user,
            wishlisted_ids=wishlisted_ids,
            cart_product_ids=cart_product_ids
        )
        for product in products
    ]

    return JsonResponse(data, safe=False)


@require_POST
def create_product_ajax(request):
    if not is_seller(request.user):
        return JsonResponse({"message": "Hanya seller yang dapat menambahkan produk."}, status=403)

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
    if product.wishlisted_by.filter(pk=request.user.pk).exists():
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
    request.session.modified = True

    return JsonResponse({"message": f'"{product.name}" berhasil ditambahkan ke keranjang!'})
