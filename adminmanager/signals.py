''' signal to remind the admin about when the quanty goes below
    the threshold value "low_stock_threshold" '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Variant
from django.core.mail import send_mail
from django.conf import settings


@receiver(post_save, sender=Variant)
def low_value_reminder(sender, instance, **kwargs):
    if instance.quantity <= instance.low_stock_threshold:
        product_name = instance.product.product_name
        subject = f"Low stock alert for {product_name}"
        message = (
            f'''The stock for {product_name} with
              RAM: {instance.ram} and ROM: {instance.internal_memory} '''
            f"has dropped to {instance.quantity}. Please restock the product."
        )
        # Send the email
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER,
                      [settings.ADMIN_EMAIL])
        except Exception as e:
            # Handle the exception (e.g., log the error)
            print(f"Failed to send low stock alert email: {e}")
