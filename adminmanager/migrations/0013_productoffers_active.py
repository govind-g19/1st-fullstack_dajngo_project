# Generated by Django 5.0.1 on 2024-06-12 04:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminmanager', '0012_productoffers_product_product_offer'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoffers',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
