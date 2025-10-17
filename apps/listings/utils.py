from django.db.models import F

from ..statistics.models import ListingView, ListingStats

def record_listing_view(listing, user=None, session_id:str=""):
    """By views: when listing views – increment"""
    ListingView.objects.create(
        listing=listing,
        user=user if (user and user.is_authenticated) else None,
        session_id=session_id or "")
    stats, _ = ListingStats.objects.get_or_create(listing=listing)

    ListingStats.objects.filter(listing=listing).update(views_count=F("views_count") + 1)