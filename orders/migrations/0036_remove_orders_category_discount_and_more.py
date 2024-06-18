# Generated by Django 5.0.1 on 2024-06-15 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0035_alter_orders_order_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orders',
            name='category_discount',
        ),
        migrations.RemoveField(
            model_name='orders',
            name='product_discount',
        ),
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='23D27A28', max_length=8, unique=True),
        ),
    ]