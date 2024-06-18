from django.contrib import admin
from .models import Address, Coupons, UserCoupons, Wallet, Transaction
from .models import WishList, Referral
# Register your models here

admin.site.register(Address)
admin.site.register(UserCoupons)
admin.site.register(Coupons)
admin.site.register(Wallet)
admin.site.register(Transaction)
admin.site.register(WishList)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code', 'referred_by', 'created_at')
    search_fields = ('user__username', 'referred_by__username')
