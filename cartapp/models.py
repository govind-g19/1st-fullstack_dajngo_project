from django.db import models
from adminmanager.models import Variant,  Product
from django.contrib.auth.models import User


# Create your models here.


class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    date_added = models.DateField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Cart {self.user}"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    added_quantity = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    date_added = models.DateField(auto_now_add=True, blank=True, null=True)

    def sub_total(self):
        return self.variant.final_price * self. added_quantity

    def __str__(self):
        return f"item {self.product.product_name}, RAM-{self.variant.ram}, ROM-{self.variant.internal_memory}, quantity-{self.added_quantity}"
