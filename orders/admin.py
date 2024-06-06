from django.contrib import admin
from .models import OrderItem, Orders, Payment, Razorpay_payment
# Register your models here.

admin.site.register(Orders)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Razorpay_payment)
