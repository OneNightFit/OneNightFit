from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
import uuid
from zoneinfo import ZoneInfo

from datetime import timedelta

RENTAL_TIME_ZONE = ZoneInfo("Asia/Jakarta")


def local_rental_date():
    return timezone.localdate(timezone=RENTAL_TIME_ZONE)

# One User one cart, cart unique to each User (OnetoOne).
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.user}"

# Catalog products are referenced by their UUID primary key.
class CartItem(models.Model):
    """Produk Catalog yang dimasukkan ke Cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    post = models.ForeignKey("inspo.Post", on_delete=models.CASCADE, related_name="cart_items", null=True, blank=True)
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="cart_items", null=True, blank=True)
    days = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(30)])
    selected = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at", "-id"] # paling baru ditambahkan di urutan teratas
        constraints = [
            models.UniqueConstraint(fields=["cart", "post"], name="unique_cart_item_per_post"),
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_item_per_product"),
        ]

    def __str__(self):
        return f"{self.product_id or self.post_id} x {self.days} hari"

class Rental(models.Model):
    """Riwayat sewa yang sudah dibayar"""
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rentals")
    product_id = models.PositiveIntegerField(null=True, blank=True)
    product_uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    rental_date = models.DateField(default=local_rental_date, db_index=True)
    product_name = models.CharField(max_length=255)
    image = models.URLField(max_length=1000, blank=True)
    store_slug = models.CharField(max_length=50)
    store_name = models.CharField(max_length=50)
    price_per_day = models.PositiveIntegerField()
    days = models.PositiveSmallIntegerField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(
            fields=["product_uuid", "rental_date"],
            name="unique_product_rental_per_day",
        )]

    @property
    def total_display(self):
        return "Rp" + f"{self.total:,}".replace(",", ".")

    @property
    def end_date(self):
        """Tanggal berakhirnya sewa (tanggal mulai + jumlah hari)."""
        start = timezone.localtime(self.created_at, RENTAL_TIME_ZONE).date()
        return start + timedelta(days=self.days)
