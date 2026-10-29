from django.db import migrations, models
from django.utils import timezone


def set_rental_dates_and_keep_latest(apps, schema_editor):
    Rental = apps.get_model("cart", "Rental")
    db = schema_editor.connection.alias
    seen = set()
    duplicate_ids = []

    rows = Rental.objects.using(db).order_by(
        "-created_at", "-id"
    ).values_list("id", "buyer_id", "product_uuid", "product_id", "created_at")
    for rental_id, buyer_id, product_uuid, product_id, created_at in rows.iterator():
        rental_date = timezone.localdate(created_at)
        Rental.objects.using(db).filter(id=rental_id).update(rental_date=rental_date)
        identity = ("legacy", product_id) if product_id is not None else ("uuid", product_uuid)
        key = (identity, rental_date)
        if key in seen:
            duplicate_ids.append(rental_id)
        else:
            seen.add(key)

    if duplicate_ids:
        Rental.objects.using(db).filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0005_latest_legacy_rental_per_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="rental",
            name="rental_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(set_rental_dates_and_keep_latest, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="rental",
            name="unique_rental_per_buyer_product",
        ),
        migrations.AlterField(
            model_name="rental",
            name="rental_date",
            field=models.DateField(db_index=True, default=timezone.localdate),
        ),
        migrations.AddConstraint(
            model_name="rental",
            constraint=models.UniqueConstraint(
                fields=("product_uuid", "rental_date"),
                name="unique_product_rental_per_day",
            ),
        ),
    ]
