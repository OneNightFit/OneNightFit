from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    class Role(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"
        
    SIZE_CHOICES = [(s, s) for s in ("XS", "S", "M", "L", "XL", "XXL")]
    STYLE_CHOICES = [
        ("elegant", "Elegant"),
        ("minimalist", "Minimalist"),
        ("vintage", "Vintage"),
        ("streetwear", "Streetwear"),
        ("classic", "Classic"),
    ]

    phone_validator = RegexValidator(
        regex=r"^(\+62|62|0)8[1-9][0-9]{6,10}$",
        message="Enter a valid Indonesian phone number, e.g. 081234567890.",
    )
    body_validators = [MinValueValidator(30), MaxValueValidator(250)]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.BUYER)
    shop_name = models.CharField(max_length=100, blank=True)  # khusus seller
    shop_description = models.TextField(max_length=300, blank=True)  # khusus seller

    phone_number = models.CharField(max_length=16, blank=True, validators=[phone_validator])
    city = models.CharField(max_length=60, blank=True)

    clothing_size = models.CharField(max_length=3, choices=SIZE_CHOICES, blank=True)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True, validators=body_validators)
    chest_cm = models.PositiveSmallIntegerField(null=True, blank=True, validators=body_validators)
    waist_cm = models.PositiveSmallIntegerField(null=True, blank=True, validators=body_validators)

    favorite_styles = models.JSONField(default=list, blank=True)  # list of STYLE_CHOICES keys

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER
    @property
    def display_name(self):
        return self.user.first_name or self.user.username

    @property
    def initials(self):
        parts = self.display_name.split()
        return "".join(p[0] for p in parts[:2]).upper()

    @property
    def masked_phone(self):
        """081234567890 -> 08**********"""
        if not self.phone_number:
            return ""
        return self.phone_number[:2] + "*" * (len(self.phone_number) - 2)

    @property
    def favorite_style_labels(self):
        labels = dict(self.STYLE_CHOICES)
        return [labels[s] for s in self.favorite_styles if s in labels]

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs): 
    if created:
        Profile.objects.create(user=instance)
