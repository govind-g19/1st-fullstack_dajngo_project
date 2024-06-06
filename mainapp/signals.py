
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserQuery
from django.core.mail import send_mail
from django.conf import settings

''' to send the mail abou the query of the user to admin email,
 whixh is saved in the settings'''


@receiver(post_save, sender=UserQuery)
def send_query_notification(sender, instance, created, **kwargs):
    if created:
        subject = 'New User Query'
        message = f'Hello Admin,\n\nYou have received a new query from {instance.user.username} ({instance.user.email}).\n\nQuery: {instance.query}\n\nPlease respond to the user at their registered email address.\n\nRegards,\nYour Website Team'
        send_mail(subject, message, settings.EMAIL_HOST_USER, [settings.ADMIN_EMAIL])
