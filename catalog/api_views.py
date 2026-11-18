from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import Product
from catalog.permissions import IsSellerOrProductOwnerOrReadOnly
from catalog.serializers import ProductSerializer


def product_queryset():
    return Product.objects.select_related("seller", "seller__profile").annotate(
        avg_score=Avg("ratings__score"),
        ratings_cnt=Count("ratings", distinct=True),
    )


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsSellerOrProductOwnerOrReadOnly])
def product_list(request):
    if request.method in ("GET", "HEAD"):
        products = product_queryset().order_by("name", "id")
        category = request.query_params.get("category", "").strip()
        query = request.query_params.get("q", "").strip()
        if category:
            products = products.filter(category=category)
        if query:
            products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
        serializer = ProductSerializer(products, many=True, context={"request": request})
        return Response(serializer.data)

    serializer = ProductSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save(seller=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsSellerOrProductOwnerOrReadOnly])
def product_detail(request, product_id):
    product = get_object_or_404(product_queryset(), pk=product_id)
    # DRF's function-view permission decorator checks view-level permissions;
    # explicitly enforce the owner check for unsafe detail requests.
    permission = IsSellerOrProductOwnerOrReadOnly()
    if not permission.has_object_permission(request, None, product):
        return Response({"detail": permission.message}, status=status.HTTP_403_FORBIDDEN)

    if request.method in ("GET", "HEAD"):
        serializer = ProductSerializer(product, context={"request": request})
        return Response(serializer.data)
    if request.method == "DELETE":
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProductSerializer(
        product,
        data=request.data,
        partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def product_wishlist(request, product_id):
    product = get_object_or_404(product_queryset(), pk=product_id)
    if product.wishlisted_by.filter(pk=request.user.pk).exists():
        product.wishlisted_by.remove(request.user)
    else:
        product.wishlisted_by.add(request.user)
    serializer = ProductSerializer(product, context={"request": request})
    return Response(serializer.data)
