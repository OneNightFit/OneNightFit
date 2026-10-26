from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from catalog.models import Product
# from temp.forms import ProductForm

def landing_page(request):
    return render(request, "index.html")


def catalog_list(request):
    """Displays all products in the catalog."""
    products = Product.objects.all()
    categories_data = [
        (code, name, products.filter(category=code).count())
        for code, name in Product.PRODUCT_CATEGORY
    ]
    context = {
        'products': products,
        'categories': categories_data,
    }
    return render(request, 'catalog.html', context)

# CRUD
def product_detail(request, id):
    return render(request, 'catalog/product_detail.html', context)


def create_product(request):
    return redirect('catalog:catalog_list')


def edit_product(request, id):
    return redirect('catalog:catalog_list')


def delete_product(request, id):
    return redirect('catalog:catalog_list')


@login_required
@require_POST
def toggle_wishlist(request, id):
    return redirect('catalog:catalog_list')