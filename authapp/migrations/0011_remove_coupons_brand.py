# Generated by Django 5.0.1 on 2024-06-09 21:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authapp', '0010_remove_coupons_max_usage_count_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coupons',
            name='brand',
        ),
    ]