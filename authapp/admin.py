from django.contrib import admin
from .models import Address, Coupons, UserCoupons, Wallet, Transaction
# Register your models here

admin.site.register(Address)
admin.site.register(UserCoupons)
admin.site.register(Coupons)
admin.site.register(Wallet)
admin.site.register(Transaction)
