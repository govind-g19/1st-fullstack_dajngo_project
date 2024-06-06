from django.db import models
from django.contrib.auth.models import User
from authapp.models import Address
from adminmanager.models import Product, Variant
import uuid

# Create your models here.
STATUS = (
        ('OrderPending', 'Orderpending'),
        ('orderfailed', 'orderfailed'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
    )

PAYMENT_METHODS = (

        ('Razorpay', 'Razorpay'),
        ('COD', 'COD'),
        ('wallet', 'wallet')
    )


class Orders(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    order_id = models.CharField(max_length=8, default=uuid.uuid4().hex[:8].upper(), unique=True)
    delivery_address = models.ForeignKey(Address, on_delete=models.CASCADE, limit_choices_to={'user': models.F('user'), 'is_primary': True})
    order_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, null=True, blank=True)
    discount_given = models.DecimalField(max_digits=8, decimal_places=2, null=False, default=00)
    shipping = models.FloatField()
    tax = models.FloatField()
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS,
                              default='Orderpending', null=True, blank=False)
    is_active = models.BooleanField(default=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"user: {self.user.username}, order_id: {self.order_id}"
    
    class Meta:
        ordering = ['-id']


class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    memmory = models.CharField(max_length=10)
    ram = models.CharField(max_length=20)
    quantity = models.IntegerField( null=False, default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=False, default=0)


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, null=False)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=100)
    amount_paid = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'payment'
        verbose_name_plural = ' payments'

    def __str__(self):
        return self.payment_method


class Razorpay_payment(models.Model):
    razorpay_payment_id = models.CharField(max_length=30, unique=True)
    amount = models.IntegerField(blank=True, null=True)
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, null=False)

    def __str__(self):
        return self.razorpay_payment_id
