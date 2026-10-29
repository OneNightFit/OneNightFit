from django.db import migrations, models


def keep_latest_rental_per_product(apps, schema_editor):
    Rental = apps.get_model("cart", "Rental")
    db = schema_editor.connection.alias
    seen = set()
    duplicate_ids = []

    rows = Rental.objects.using(db).order_by(
        "buyer_id", "product_uuid", "-created_at", "-id"
    ).values_list("id", "buyer_id", "product_uuid")
    for rental_id, buyer_id, product_uuid in rows.iterator():
        key = (buyer_id, product_uuid)
        if key in seen:
            duplicate_ids.append(rental_id)
        else:
            seen.add(key)

    if duplicate_ids:
        Rental.objects.using(db).filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0003_catalog_product_cart"),
    ]

    operations = [
        migrations.RunPython(keep_latest_rental_per_product, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="rental",
            constraint=models.UniqueConstraint(
                fields=("buyer", "product_uuid"),
                name="unique_rental_per_buyer_product",
            ),
        ),
    ]
