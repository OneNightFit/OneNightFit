import uuid
from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User 


class Product(models.Model):
    PRODUCT_CATEGORY = [
        ('tshirts', 'T-Shirts'),
        ('hoodies', 'Hoodies & Sweatshirts'),
        ('polos', 'Polos'),
        ('casual_shirts', 'Casual Shirts'),
        ('sweaters', 'Sweaters'),
        ('tank_tops', 'Tank Tops'),
        
        ('jeans', 'Jeans'),
        ('sweatpants', 'Sweatpants & Joggers'),
        ('cargo_pants', 'Cargo Pants'),
        ('chinos', 'Chinos'),
        ('shorts', 'Shorts'),
        ('skirts', 'Skirts'),
        
        ('denim_jackets', 'Denim Jackets'),
        ('bomber_jackets', 'Bomber Jackets'),
        ('windbreakers', 'Windbreakers'),
        ('puffer_jackets', 'Puffer Jackets'),
        ('cardigans', 'Cardigans'),
        
        ('tracksuits', 'Tracksuits'),
        ('gym_tees', 'Gym Tees'),
        ('athletic_shorts', 'Athletic Shorts'),
        ('leggings', 'Leggings'),
        ('pajamas', 'Pajamas'),
        
        ('blazers', 'Blazers & Jackets'),
        ('dress_shirts', 'Dress Shirts'),
        ('trousers', 'Trousers'),
        ('dresses', 'Dresses'),
        
        ('bags', 'Backpacks & Totes'),
        ('headwear', 'Caps & Beanies'),
        ('socks', 'Socks'),
        ('footwear', 'Sneakers & Shoes'),
    ]

    PRODUCT_MATERIALS = [
        ('100_cotton', '100% Cotton'),
        ('cotton_poly', 'Cotton-Polyester Blend'),
        ('denim', 'Denim (Cotton/Spandex)'),
        ('fleece', 'Fleece / French Terry'),
        ('poly_nylon', 'Polyester / Nylon Blend'),
        ('linen_blend', 'Linen Blend'),
        ('rayon_viscose', 'Rayon / Viscose'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField()
    category = models.CharField(max_length=20, choices=PRODUCT_CATEGORY)
    size = models.CharField(max_length=3, choices=PRODUCT_SIZE)
    wishlisted_by = models.ManyToManyField(
        User, related_name="wishlisted_product", blank=True
    )
    rated_by = models.ManyToManyField(
        User, related_name="rated_by", blank=True
    )
    def __str__(self):
        return self.title
    
    @property
    def is_ongoing(self):
        return self.ended_at is None

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

    