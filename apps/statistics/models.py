from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models

from ..core.models import TimeStampedModel

class ListingView(TimeStampedModel):
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="stats_views",
        verbose_name=_("Listing")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User")
    )
    session_id = models.CharField(max_length=64, blank=True, verbose_name=_("Session ID"))

    class Meta:
        verbose_name = "Listing view"
        verbose_name_plural = "Listing views"


class SearchQuery(TimeStampedModel):
    """
    Search query keywords + params.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User")
    )
    session_id = models.CharField(max_length=64, blank=True, verbose_name=_("Session ID"))
    keywords = models.CharField(max_length=255, verbose_name=_("Keywords"))
    params = models.JSONField(default=dict, blank=True, verbose_name=_("Params"))

    class Meta:
        verbose_name = "Search query"
        verbose_name_plural = "Search queries"


class SearchQueryStats(TimeStampedModel):
    """
    Search query statistics.
    """
    keywords = models.CharField(max_length=255, unique=True, verbose_name=_("Keywords"))
    count = models.PositiveIntegerField(default=0, verbose_name=_("Count"))

    class Meta:
        verbose_name = "Search keywords stats"
        verbose_name_plural = "Search keywords stats"


class ListingStats(TimeStampedModel):
    """
    Statistics for a listing.

    - views_count: total number of views
    - reviews_count: number of reviews
    - avg_rating: average rating
    - popularity: views, reviews, rating
    """
    listing = models.OneToOneField(
        "listings.Listing",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="listing_stats",
        verbose_name=_("Listing")
    )
    views_count = models.PositiveIntegerField(default=0, verbose_name=_("Views count"))
    reviews_count = models.PositiveIntegerField(default=0, verbose_name=_("Reviews count"))
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name=_("Avg rating"))

    class Meta:
        verbose_name = "Listing stats"
        verbose_name_plural = "Listing stats"
