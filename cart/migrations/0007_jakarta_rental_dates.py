from zoneinfo import ZoneInfo

import cart.models
from django.db import migrations, models
from django.utils import timezone


JAKARTA = ZoneInfo("Asia/Jakarta")


def use_jakarta_dates_and_keep_latest(apps, schema_editor):
    Rental = apps.get_model("cart", "Rental")
    db = schema_editor.connection.alias
    seen = set()
    duplicate_ids = []

    rows = Rental.objects.using(db).order_by("-created_at", "-id").values_list(
        "id", "product_uuid", "created_at"
    )
    for rental_id, product_uuid, created_at in rows.iterator():
        rental_date = timezone.localtime(created_at, JAKARTA).date()
        Rental.objects.using(db).filter(id=rental_id).update(rental_date=rental_date)
        key = (product_uuid, rental_date)
        if key in seen:
            duplicate_ids.append(rental_id)
        else:
            seen.add(key)

    if duplicate_ids:
        Rental.objects.using(db).filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [("cart", "0006_daily_product_rentals")]

    operations = [
        migrations.RemoveConstraint(
            model_name="rental",
            name="unique_product_rental_per_day",
        ),
        migrations.RunPython(use_jakarta_dates_and_keep_latest, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="rental",
            name="rental_date",
            field=models.DateField(db_index=True, default=cart.models.local_rental_date),
        ),
        migrations.AddConstraint(
            model_name="rental",
            constraint=models.UniqueConstraint(
                fields=("product_uuid", "rental_date"),
                name="unique_product_rental_per_day",
            ),
        ),
    ]
