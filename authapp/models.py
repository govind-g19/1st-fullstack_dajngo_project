from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from adminmanager.models import Category, Product, Variant
from decimal import Decimal
# Create your models here.


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    house_address = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    land_mark = models.CharField(max_length=200, null=True, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.second_name}"

    class Meta:
        ordering = ['-id']


# to create coupon.
class Coupons(models.Model):
    coupon_code = models.UUIDField(default=uuid.uuid4,
                                   editable=False,
                                   unique=True)
    description = models.TextField()
    minimum_amount = models.IntegerField()
    discount = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    def __str__(self):
        return f"code-{self.coupon_code}"

    def is_valid(self):
        now = timezone.now()
        return self.valid_from <= now <= self.valid_to

    def is_expired(self):
        now = timezone.now()
        return now > self.valid_to

    def is_valid_discount(self):
        return self.discount > self.minimum_amount


class UserCoupons(models.Model):

    # used coupons

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupons, on_delete=models.CASCADE)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.coupon.coupon_code}"


# wallet
class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2,
                                  default=Decimal('0.00'))

    def __str__(self):
        return f"{self.user.username}'s wallet"


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=6,
                                        choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'''{self.transaction_type} of
        {self.amount} to
        {self.wallet.user.username}'s wallet on
        {self.timestamp}'''


class WishList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'variant', 'user')

    def __str__(self):
        return f''' {self.user.username}-{self.product.product_name}
        ram{self.variant.ram} and rom{self.variant.internal_memory}'''
