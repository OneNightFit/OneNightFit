import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0002_rental"),
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rental",
            name="product_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="post",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart_items",
                to="inspo.post",
            ),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart_items",
                to="catalog.product",
            ),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                fields=("cart", "product"), name="unique_cart_item_per_product"
            ),
        ),
        migrations.AddField(
            model_name="rental",
            name="product_uuid",
            field=models.UUIDField(default=uuid.uuid4, db_index=True, editable=False),
        ),
    ]
