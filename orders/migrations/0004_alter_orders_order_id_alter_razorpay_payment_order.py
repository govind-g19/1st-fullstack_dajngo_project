# Generated by Django 5.0.1 on 2024-06-30 00:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_alter_orders_order_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='5367F11F', max_length=8, unique=True),
        ),
        migrations.AlterField(
            model_name='razorpay_payment',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='orders.orders'),
        ),
    ]
