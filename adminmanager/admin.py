from django.contrib import admin

# Register your models here.
from .models import Category, Product, ProductImage, Variant, ReviewRating
# ,ProductColor,ProductRam,ProductRom,ProductVariant,VariantImage

admin.site.register(Category),
admin.site.register(Product),
admin.site.register(ProductImage)
# admin.site.register( ProductRom)
# admin.site.register( ProductRam)
# admin.site.register( ProductColor)
# admin.site.register( ProductVariant)
admin.site.register(Variant)
admin.site.register(ReviewRating)
