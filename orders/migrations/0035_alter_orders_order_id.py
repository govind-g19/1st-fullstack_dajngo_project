# Generated by Django 5.0.1 on 2024-06-14 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0034_orderitem_category_discount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_id',
            field=models.CharField(default='DA2C8D03', max_length=8, unique=True),
        ),
    ]
