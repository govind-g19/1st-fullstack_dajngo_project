# Generated by Django 5.0.1 on 2024-03-08 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_rename_variantn_orderitem_variant_alter_orders_cart_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='70985CC8', max_length=8, unique=True),
        ),
    ]
