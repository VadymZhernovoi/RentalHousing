from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..listings.models import Listing
from ..bookings.models import Booking, StatusBooking
from ..statistics.models import ListingStats
from ..reviews.models import Review

@receiver(post_save, sender=Listing)
def recalc_total_cost_bookings_on_listing_change(sender, instance: Listing, created, update_fields, **kwargs):
    """Recalculates total_cost if the price changes (only PENDING)"""
    if created:
        return
    if update_fields and "price" not in update_fields:
        return

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