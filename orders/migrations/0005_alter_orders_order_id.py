# Generated by Django 5.0.1 on 2024-06-30 05:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_alter_orders_order_id_alter_razorpay_payment_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='F6A88DE0', max_length=8, unique=True),
        ),
    ]
