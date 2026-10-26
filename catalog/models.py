import uuid
from django.db import models
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User 


class Product(models.Model):
    PRODUCT_CATEGORY = [
        ("electronics", "Electronics"),
        ("jewelery", "Jewelery"),
        ("men_clothing", "Men's Clothing"),
        ("women_clothing", "Women's Clothing"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(decimal_places=3, max_digits=8)
    category = models.CharField(max_length=50, choices=PRODUCT_CATEGORY)
    wishlisted_by = models.ManyToManyField(
        User, related_name="wishlisted_product", blank=True
    )
    rated_by = models.ManyToManyField(
        User, related_name="rated_by", blank=True
    )
    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        avg = self.ratings.aggregate(Avg('score'))['score__avg']
        return round(avg, 1) if avg else 0.0

    @property
    def rating_count(self):
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