from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSellerOrProductOwnerOrReadOnly(BasePermission):
    """Allow public reads, seller product creation, and owner-only changes."""

    message = "Only the product's seller can change it."

    @staticmethod
    def is_seller(user):
        return bool(
            user.is_authenticated
            and getattr(getattr(user, "profile", None), "is_seller", False)
        )

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not self.is_seller(request.user):
            return False
        # New products are always attached to the authenticated seller.
        if request.method == "POST" and not getattr(view, "kwargs", {}).get("product_id"):
            return True
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return self.is_seller(request.user) and obj.seller_id == request.user.pk
