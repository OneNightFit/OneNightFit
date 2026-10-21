import requests
from django.core.management.base import BaseCommand, CommandError

from inspo.models import Post, Tag


class Command(BaseCommand):
    help = "Impor produk dari Fake Store API ke database"

    def handle(self, *args, **options):
        try:
            res = requests.get("https://fakestoreapi.com/products", timeout=10)
            res.raise_for_status()
            items = res.json()
        except (requests.RequestException, ValueError) as e:
            raise CommandError(f"Gagal mengambil data API: {e}")

        baru = 0
        for item in items:
            tag, _ = Tag.objects.get_or_create(name=item["category"][:30])
            _, is_new = Post.objects.update_or_create(
                external_id=item["id"],
                defaults={
                    "title": item["title"][:100],
                    "caption": item["description"][:1000],
                    "image_url": item["image"],
                    "price": item["price"],
                    "tag": tag,
                },
            )
            baru += is_new

        self.stdout.write(self.style.SUCCESS(
            f"Selesai: {baru} data baru, {len(items) - baru} diperbarui."
        ))