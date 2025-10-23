from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db.models import Q
from django.utils import timezone

from ..core.enums import Roles
from ..core.utils import get_user_email
from .models import Booking, StatusBooking
from ..core.mails import send_safe_mail

@receiver(pre_save, sender=Booking)
def task_pre_save_capture_old_status(sender, instance: Booking, **kwargs):
    """
    Before saving, we read its previous status from the database and put it in _old_status
    """
    if instance.pk:
        try:
            old = Booking.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Booking)
def decline_overlapping_pending_on_status_approve(sender, instance: Booking, created, update_fields, **kwargs):
    """
    If the current booking is APPROVED, all overlapping PENDING bookings in the same listing are moved to DECLINED.
    Intersection of intervals: existing.start < current.end AND existing.end > current.start.
    """
    if instance.status != StatusBooking.APPROVED.value:
        return
    if not created and update_fields is not None and "status" not in update_fields:
        return

    # does not take into account old bookings whose check-out has already occurred
    today = timezone.localdate()
    # All PENDING for this listing that overlap in dates with the current booking
    queryset = (Booking.objects
          .filter(listing=instance.listing, status=StatusBooking.PENDING.value, end_date__gt=today)
          .filter(Q(start_date__lt=instance.end_date) & Q(end_date__gt=instance.start_date))
          .exclude(pk=instance.pk))
    try:
        queryset.update(status=StatusBooking.DECLINED.value, reason_cancel=f"Auto-declined due to overlap with approved booking {instance.pk}")
    except Exception:
        queryset.update(status=StatusBooking.DECLINED.value)

@receiver(post_save, sender=Booking)
def send_email_to(sender, instance: Booking, created, update_fields, **kwargs):
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
            old_status = getattr(instance, "_old_status", None)
            new_status = instance.status
            subject_to_renter = subject_to_lessor = \
                f"The reservation status changed from '{old_status}' to '{new_status}'" if new_status != old_status \
                    else "Booking has been changed."
            message = (f"Booking {instance.listing.title}  has been changed (ID: {instance.id}). \n"
                       f"Current state: from {instance.start_date.isoformat()} to {instance.end_date.isoformat()}, "
                       f"total cost: {instance.total_cost}, status: {instance.status}.")
        if to_renter_email:
            _ = send_safe_mail(subject_to_renter, message, to_renter_email)
        if to_lessor_email:
            _ = send_safe_mail(subject_to_lessor, message, to_lessor_email)

