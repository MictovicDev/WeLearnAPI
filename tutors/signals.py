# tutors/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TutorProfile
from payment.connect_service import ConnectService
import logging

logger = logging.getLogger("stripe")


@receiver(post_save, sender=TutorProfile)
def create_stripe_connect_account(sender, instance, created, **kwargs):
    if created and not instance.stripe_connect_account_id:
        try:
            ConnectService().create_connected_account(instance)
        except Exception:
            logger.exception(
                "Failed to create Stripe connected account. tutor_profile_id=%s",
                instance.id,
            )