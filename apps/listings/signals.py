from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from ..listings.models import Listing
from ..bookings.models import Booking, StatusBooking
from ..statistics.models import ListingStats
from ..reviews.models import Review
from ..core.enums import Roles
from ..core.utils import get_user_email
from RentalHousing.settings import DEFAULT_FROM_EMAIL
from ..core.mails import send_safe_mail

@receiver(pre_save, sender=Listing)
def listing_pre_save_capture_old_status(sender, instance: Listing, **kwargs):
    """
    Before saving listing, we read the previous status from the database and put it in _old_status
    """
    if instance.pk:
        try:
            old = Listing.objects.get(pk=instance.pk)
            instance._old_status = old.is_active
        except Listing.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Listing)
def send_email_bookings_on_change(sender, instance: Listing, created, update_fields, **kwargs):
    """
    Sends an email to the listing owner
    """
    to_email = get_user_email(instance, Roles.LESSOR)
    if to_email:
        if created:
            subject = f"Listing has been created."
            message = f"Listing {instance.title} (ID: {instance.id}) has been created."
        else:
            subject = f"Listing has been changed."
            message = f"Listing {instance.title} (ID: {instance.id}) has been changed."
            old_status = getattr(instance, "_old_status", None)
            if instance.is_active != old_status:
                message += f" New status is {'"INACTIVE"' if instance.is_active else '"ACTIVE"'}."

        _ = send_safe_mail(subject, message, to_email)

@receiver(post_save, sender=Listing)
def recalc_total_cost_bookings_on_change(sender, instance: Listing, created, update_fields, **kwargs):
    """
    Recalculates total_cost if the price changes (only PENDING)
    """
    if created or update_fields and "price" not in update_fields:
        return
    # Recalculates total_cost if the price changes (only PENDING)
    queryset = Booking.objects.filter(listing=instance, status=StatusBooking.PENDING.value)
    for booking in queryset.only("id", "start_date", "end_date", "total_cost", "listing_id"):
        booking.total_cost = booking.calc_total_cost()
        booking.save(update_fields=["total_cost"])

@receiver([post_save, post_delete], sender=Review)
def update_reviews_count(sender, instance, **kwargs):
    """Counts the number of reviews"""
    listing = instance.listing
    stats, _ = ListingStats.objects.get_or_create(listing=listing)
    stats.reviews_count = Review.objects.filter(listing=listing).count()

    stats.save(update_fields=["reviews_count", "updated_at"])

