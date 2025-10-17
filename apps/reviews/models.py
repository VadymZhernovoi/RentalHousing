from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from ..bookings.models import Booking
from ..listings.models import Listing
from ..core.models import TimeStampedModel

class Review(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review", verbose_name=_("Booking"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Author")
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("Listing"))
    rating = models.PositiveSmallIntegerField(null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],  # rating can be from 1 to 5
        verbose_name=_("Rating")
    )
    comment = models.TextField(null=True, blank=True, verbose_name=_("Comment"))
    owner_comment = models.TextField(null=True, blank=True, verbose_name=_("Owner comment"))
    is_valid = models.BooleanField(default=True, verbose_name=_("Is valid"))

    class Meta:
        permissions = [
            ("owner_comment", "Can write owner comment"),  # право писать owner_comment
            ("moderate_review", "Can moderate reviews (is_valid)"),
        ]
        indexes = [models.Index(fields=["listing", "created_at"])]

