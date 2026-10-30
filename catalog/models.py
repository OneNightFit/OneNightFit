import uuid
from django.db import models
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User 
import random

def get_random_size():
    return random.choice(['S', 'M', 'L', 'XL'])

class Product(models.Model):
    PRODUCT_CATEGORY = [
        ("electronics", "Electronics"),
        ("jewelery", "Jewelery"),
        ("men_clothing", "Men's Clothing"),
        ("women_clothing", "Women's Clothing"),
    ]

    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    description = models.TextField()
    image = models.URLField(max_length=1000, null=True, blank=True)
    image_file = models.ImageField(upload_to="catalog/products/", blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    category = models.CharField(max_length=50, choices=PRODUCT_CATEGORY)
    size = models.CharField(max_length=2, choices=SIZE_CHOICES, default=get_random_size)
    wishlisted_by = models.ManyToManyField(
        User, related_name="wishlisted_product", blank=True
    )
    def __str__(self):
        return self.name

    @property
    def seller_display(self):
        """Return shop_name or display name if seller has a profile, else username or hyphen."""
        if not self.seller:
            return "-"
        profile = getattr(self.seller, "profile", None)
        if profile and profile.shop_name:
            return profile.shop_name
        return self.seller.get_full_name() or self.seller.username

    @property
    def image_src(self):
        """Return the uploaded image URL, or the legacy external image URL."""
        return self.image_file.url if self.image_file else (self.image or "")

    @property
    def average_rating(self):
        annotated = getattr(self, "avg_score", None)
        if annotated is not None:
            return round(annotated, 1) if annotated else 0.0
        avg = self.ratings.aggregate(Avg('score'))['score__avg']
        return round(avg, 1) if avg else 0.0

    @property
    def rating_count(self):
        annotated = getattr(self, "ratings_cnt", None)
        if annotated is not None:
            return annotated
        return self.ratings.count()

    def is_wishlisted_by(self, user):
        if not user.is_authenticated:
            return False
        return self.wishlisted_by.filter(id=user.id).exists()

class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_ratings")
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        # Ensures a user can only rate a specific product once
        unique_together = ('product', 'user') 

    def __str__(self):
        return f"{self.user.username} rated {self.product.name} {self.score}/5"
