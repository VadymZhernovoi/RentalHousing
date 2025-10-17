from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..statistics.models import ListingStats
from ..reviews.models import Review

@receiver([post_save, post_delete], sender=Review)
def update_reviews_count(sender, instance, **kwargs):
    """Counts the number of reviews"""
    listing = instance.listing
    stats, _ = ListingStats.objects.get_or_create(listing=listing)

    stats.reviews_count = Review.objects.filter(listing=listing).count()

    stats.save(update_fields=["reviews_count", "updated_at"])