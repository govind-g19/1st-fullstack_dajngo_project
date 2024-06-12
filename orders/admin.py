from django.contrib import admin
from .models import OrderItem, Orders, Payment, Razorpay_payment

# Register your models here.
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Razorpay_payment)

@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'order_date', 'status', 'grand_total')
    list_filter = ('status', 'order_date', 'payment_method')
    search_fields = ('order_id', 'user__username')
    date_hierarchy = 'order_date'
