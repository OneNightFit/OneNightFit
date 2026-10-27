from django.shortcuts import render

def cart_page(request):
    return render(request, "cart/cart.html")

def checkout_page(request):
    return render(request, "cart/checkout.html")