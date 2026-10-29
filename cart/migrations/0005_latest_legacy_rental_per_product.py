from django.db import migrations


def keep_latest_legacy_rental(apps, schema_editor):
    Rental = apps.get_model("cart", "Rental")
    db = schema_editor.connection.alias
    seen = set()
    duplicate_ids = []

    rows = Rental.objects.using(db).filter(product_id__isnull=False).order_by(
        "buyer_id", "product_id", "-created_at", "-id"
    ).values_list("id", "buyer_id", "product_id")
    for rental_id, buyer_id, product_id in rows.iterator():
        key = (buyer_id, product_id)
        if key in seen:
            duplicate_ids.append(rental_id)
        else:
            seen.add(key)

    if duplicate_ids:
        Rental.objects.using(db).filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0004_unique_user_product_rental"),
    ]

    operations = [
        migrations.RunPython(keep_latest_legacy_rental, migrations.RunPython.noop),
    ]
