# Generated by Django 5.0.1 on 2024-05-14 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0015_alter_orders_order_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='6EEEA6B4', max_length=8, unique=True),
        ),
    ]
