from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# One User one cart, cart unique to each User (OnetoOne).
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.user}"

class CartItem(models.Model):
    """Produk yang dimasukkan ke Cart dari Catalog dengan default tidak ada yang terpilih untuk Checkout"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    post = models.ForeignKey("inspo.Post", on_delete=models.CASCADE, related_name="cart_items")
    days = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(30)])
    selected = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at", "-id"] # paling baru ditambahkan di urutan teratas
        constraints = [
            models.UniqueConstraint(fields=["cart", "post"], name="unique_cart_item_per_post"),
        ]

    def __str__(self):
        return f"{self.post_id} x {self.days} hari"