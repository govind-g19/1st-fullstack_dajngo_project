# Generated by Django 5.0.1 on 2024-05-29 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminmanager', '0007_variant_low_stock_threshold'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='quantity',
            field=models.IntegerField(default=1000),
        ),
    ]
