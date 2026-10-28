import requests
from django.core.management.base import BaseCommand, CommandError
from catalog.models import Product

class Command(BaseCommand):
    help = "Impor produk dari Fake Store API ke database Katalog"

    def handle(self, *args, **options):
        try:
            res = requests.get("https://fakestoreapi.com/products", timeout=10)
            res.raise_for_status()
            items = res.json()
        except (requests.RequestException, ValueError) as e:
            raise CommandError(f"Gagal mengambil data API: {e}")

        baru = 0
        for item in items:
            # Karena category di Product Anda memakai system Choices terbatas, 
            # Petakan ke keys yang ada (misal: 'men_clothing', 'jewelery')
            api_cat = item["category"]
            category_mapping = {
                "electronics": "electronics",
                "jewelery": "jewelery",
                "men's clothing": "men_clothing",
                "women's clothing": "women_clothing"
            }
            mapped_category = category_mapping.get(api_cat, "men_clothing")

            _, is_new = Product.objects.update_or_create(
                # Anda tidak memiliki field external_id, jadi kita cocokkan berdasarkan nama
                name=item["title"][:255],
                defaults={
                    "description": item["description"],
                    "price": item["price"],
                    "category": mapped_category,
                    # Jika model Product Anda belum memiliki image_url, Anda perlu menambahkannya ke model Product
                },
            )
            baru += is_new
            
        self.stdout.write(self.style.SUCCESS(
            f"Selesai: {baru} data baru, {len(items) - baru} diperbarui."
        ))