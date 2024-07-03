from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class UserQuery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True)


class Wallet_Razorpay_payment(models.Model):
    razorpay_payment_id = models.CharField(max_length=30, unique=True)
    amount = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             blank=True, null=True)

    def __str__(self):
        return f'''the user {self.user.username} '''
