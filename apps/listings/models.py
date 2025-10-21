from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from ..core.enums import TypesHousing, Availability
from ..core.models import TimeStampedModel

class Listing(TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings", verbose_name=_("Owner")
    )
    title = models.CharField(max_length=120, verbose_name=_("Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    location = models.CharField(max_length=255, verbose_name=_("Location"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("City"))
    district = models.CharField(max_length=100, blank=True, verbose_name=_("District"))
    country = models.CharField(max_length=2, default="DE", verbose_name=_("Country"))
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Price"))
    currency = models.CharField(max_length=3, default="EUR", verbose_name=_("Currency"))
    span_days_max = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Max Span Days"))
    span_days_min = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Min Span Days"))

    rooms = models.PositiveSmallIntegerField(default=1, verbose_name=_("Rooms"))
    guests_max = models.PositiveSmallIntegerField(default=0, verbose_name=_("Max Guests"))
    baby_crib_max = models.PositiveSmallIntegerField(default=0, verbose_name=_("Max Baby Cribs"))
    has_kitchen = models.CharField(
        max_length=1,
        choices=Availability.choices,
        default=Availability.UNKNOWN,
        verbose_name=_("Kitchen Available"))
    parking_available = models.CharField(
        max_length=1,
        choices=Availability.choices,
        default=Availability.UNKNOWN,
        verbose_name=_("Parking Available"))
    pets_possible = models.CharField(
        max_length=1,
        choices=Availability.choices,
        default=Availability.UNKNOWN,
        verbose_name=_("Pets Possible"))

    type_housing = models.CharField(
        max_length=20,
        choices=TypesHousing.choices,
        default=TypesHousing.APARTMENT,
        verbose_name=_("Type"))

    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        verbose_name = 'Listing'
        verbose_name_plural = 'Listings'
        permissions = [
            ("toggle_active_listing", "Can activate/deactivate listing"),
            ("view_inactive_listing", "Can view inactive listings"),
            ("view_all_listings", "Can view all listings (active + inactive)"),
        ]

    def __str__(self):
        return f"{self.title} ({self.location})"
