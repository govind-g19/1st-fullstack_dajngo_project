from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class UserQuery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField(max_length=500)
    timestamp = models.DateTimeField(auto_now_add=True)
