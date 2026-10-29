import random
from decimal import Decimal

import requests
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from catalog.models import Product
from authentication.models import Profile

SELLERS = [
    ("forza_ferrari", "Forza Ferrari"),
    ("knuckle_velvet", "Knuckle Velvet"),
    ("alley_rose", "Alley Rose"),
    ("ex_machina", "Ex Machina"),
]

CATEGORY_MAPPING = {
    "electronics": "electronics",
    "jewelery": "jewelery",
    "men's clothing": "men_clothing",
    "women's clothing": "women_clothing",
}


def get_or_create_sellers():
    sellers = []
    for username, display_name in SELLERS:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": display_name},
        )
        if created:
            user.set_unusable_password()
            user.save()

        profile = getattr(user, "profile", None)
        if profile is None:
            raise CommandError(
                f"User '{username}' tidak punya profile. Cek signal pembuat Profile."
            )
        if not profile.is_seller:
            profile.role = Profile.Role.SELLER
            profile.shop_name = profile.shop_name or display_name
            profile.save()

        sellers.append(user)
    return sellers


class Command(BaseCommand):
    help = "Impor produk dari Fake Store API ke database Katalog"

    def handle(self, *args, **options):
        try:
            res = requests.get("https://fakestoreapi.com/products", timeout=10)
            res.raise_for_status()
            items = res.json()
        except (requests.RequestException, ValueError) as e:
            raise CommandError(f"Gagal mengambil data API: {e}")

        sellers = get_or_create_sellers()
        size_keys = [code for code, _ in Product.SIZE_CHOICES]

        baru = 0
        for item in items:
            fields = {
                "description": item["description"],
                "price": Decimal(str(item["price"])),
                "category": CATEGORY_MAPPING.get(item["category"], "men_clothing"),
                "image": item["image"],
            }
            name = item["title"][:255]

            product = Product.objects.filter(name=name, seller__in=sellers).first()
            if product:
                # Sudah pernah diimpor: seller & size dibiarkan, tidak diacak ulang
                for key, value in fields.items():
                    setattr(product, key, value)
                product.save()
            else:
                Product.objects.create(
                    name=name,
                    seller=random.choice(sellers),
                    size=random.choice(size_keys),
                    **fields,
                )
                baru += 1

        self.stdout.write(self.style.SUCCESS(
            f"Selesai: {baru} data baru, {len(items) - baru} diperbarui."
        ))