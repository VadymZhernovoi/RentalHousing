from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Booking
from ..core.enums import Roles
from ..core.utils import get_user_email
from RentalHousing.settings import DEFAULT_FROM_EMAIL


@receiver(post_save, sender=Booking)
def send_email(sender, instance: Booking, created, update_fields, **kwargs):
    """Sends an email to the Booking owner and booking renter."""
    to_renter_email = get_user_email(instance, Roles.RENTER)
    to_lessor_email = get_user_email(instance, Roles.LESSOR)
    if to_renter_email or to_lessor_email:
        if created:
            subject_to_renter = f"You have by user '{to_lessor_email}' booked housing."
            subject_to_lessor = (f"Your housing has been booked by user '{to_renter_email}'.")
            message = (f"Booking {instance.listing.title} (ID: {instance.id}) "
                       f"from {instance.start_date.isoformat()} to {instance.end_date.isoformat()} "
                       f"(total cost: {instance.total_cost}) has been created.")
        else:
            subject_to_renter = subject_to_lessor = f"Booking has been changed."
            message = (f"Booking {instance.listing.title}  has been changed (ID: {instance.id}). \n"
                       f"Current state: from {instance.start_date.isoformat()} to {instance.end_date.isoformat()}, "
                       f"total cost: {instance.total_cost}, status: {instance.status}.")
        if to_renter_email:
            send_mail(
                subject_to_renter,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", DEFAULT_FROM_EMAIL),
                [to_renter_email],
                fail_silently=True,
            )
        if to_lessor_email:
            send_mail(
                subject_to_lessor,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", DEFAULT_FROM_EMAIL),
                [to_lessor_email],
                fail_silently=True,
            )

