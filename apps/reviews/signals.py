from django.db.models.aggregates import Avg, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..core.utils import get_user_email
from ..core.enums import Roles
from ..statistics.models import ListingStats
from ..reviews.models import Review
from ..core.mails import send_safe_mail


@receiver([post_save, post_delete], sender=Review)
def update_reviews_count(sender, instance, **kwargs):
    """
    Counts the number of reviews and averages rating.
    """
    listing = instance.listing
    stats, _ = ListingStats.objects.get_or_create(listing=listing)
    stats.reviews_count = Review.objects.filter(listing=listing).count()
    agr = Review.objects.filter(listing=listing, is_valid=True).aggregate(avg=Avg("rating"), cnt=Count("id"))
    stats.avg_rating = agr["avg"] or 0
    stats.reviews_count = agr["cnt"] or 0

    stats.save(update_fields=["reviews_count", "avg_rating", "updated_at"])


@receiver(post_save, sender=Review)
def send_email(sender, instance: Review, created, update_fields, **kwargs):
    """
    Sends an email to the Booking owner and booking renter.
    """
    to_renter_email = get_user_email(instance, 'author')
    to_lessor_email = get_user_email(instance, Roles.LESSOR)
    if to_renter_email or to_lessor_email:
        listing = instance.listing
        if created:
            subject_to_renter = f"You left a review for the housing {listing.title}."
            subject_to_lessor = (f"A review was received on your housing by user '{to_renter_email}'.")
        else:
            subject_to_renter = subject_to_lessor = f"A review for the housing {listing.title} has been changed."

        message = (f"Review of booking {instance.listing.title}"
                   f"from {instance.booking.start_date.isoformat()} to {instance.booking.end_date.isoformat()}. \n"
                   f"Renter comment: {instance.comment} \n"
                   f"Rating: {instance.rating} \n"
                   f"Lessor comment: {instance.owner_comment} \n"
                   f"Is valid: {instance.is_valid}")

        if to_renter_email:
            _ = send_safe_mail(subject_to_renter, message, to_renter_email)

        if to_lessor_email:
            _ = send_safe_mail(subject_to_lessor, message, to_lessor_email)

