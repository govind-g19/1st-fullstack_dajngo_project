# Generated by Django 5.0.1 on 2024-06-17 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0040_orderitem_offer_price_alter_orders_order_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='61F24999', max_length=8, unique=True),
        ),
    ]