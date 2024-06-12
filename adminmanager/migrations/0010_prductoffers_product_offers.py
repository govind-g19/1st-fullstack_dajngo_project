# Generated by Django 5.0.1 on 2024-06-10 13:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminmanager', '0009_remove_product_price_remove_product_quantity'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrductOffers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_offer_name', models.CharField(max_length=100)),
                ('discount', models.IntegerField(default=0)),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='offers',
            field=models.ManyToManyField(to='adminmanager.prductoffers'),
        ),
    ]
