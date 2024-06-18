from django.contrib import admin

# Register your models here.
from .models import Category, Product, ProductImage, Variant, ReviewRating
from .models import ProductOffers, CategoryOffers


admin.site.register(Category),
admin.site.register(Product),
admin.site.register(ProductImage)
admin.site.register(ProductOffers)
admin.site.register(CategoryOffers)
admin.site.register(Variant)
admin.site.register(ReviewRating)
