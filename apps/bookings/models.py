from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from ..listings.models import Listing
from ..core.enums import StatusBooking, Availability
from ..core.models import TimeStampedModel
from .validators import check_booking_validations


class Booking(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings", verbose_name=_("Listing"))
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name=_("Renter")
    )
    start_date = models.DateField(verbose_name=_("Start date"))
    end_date = models.DateField(verbose_name=_("End date"))
    cancel_hours = models.PositiveIntegerField(
        default=48,
        help_text=_("How many hours before 00:00 of start_date cancellation is allowed. 0 = non-refundable."),
        verbose_name=_("Hours until cancellation")
    )
    reason_cancel = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Reason cancellation"))

    guests = models.PositiveIntegerField(default=1, verbose_name=_("Guests"))
    baby_cribs = models.PositiveIntegerField(default=0, verbose_name=_("Baby Cribs"))
    kitchen_needed = models.BooleanField(default=None, null=True, blank=True, verbose_name=_("Kitchen needed"))
    parking_needed = models.BooleanField(default=None, null=True, blank=True, verbose_name=_("Parking needed"))
    pets = models.BooleanField(default=False, null=None, blank=True, verbose_name=_("Pets"))

    status = models.CharField(
        max_length=10,
        choices=StatusBooking.choices, default=StatusBooking.PENDING,
        verbose_name=_("Status")
    )
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Total cost"))

    class Meta:
        permissions = [
            ("can_approve", "Can approve bookings"),
            ("can_decline", "Can decline bookings"),
            ("can_complete", "Can mark bookings as completed"),
            ("can_cancel", "Can cancel any booking"),
        ]

    def get_cancel_deadline(self, tz=None) -> timezone.datetime:
        """
        Calculates the datetime deadline for cancellation.
        If cancel_hours == 0 → deadline cannot be canceled.
        The starting point is 00:00 local time on the start_date.
        :param tz: local time zone
        :return: the datetime deadline for cancellation.
        """
        if self.cancel_hours == 0: # the window is always closed
            return timezone.now() - timezone.timedelta(days=365 * 10)
        tz = tz or timezone.get_current_timezone()
        start_dt = timezone.make_aware(
            timezone.datetime(self.start_date.year, self.start_date.month, self.start_date.day, 0, 0, 0), tz)
        return start_dt - timezone.timedelta(hours=self.cancel_hours)

    def is_can_be_cancellation(self) -> bool:
        return timezone.now() <= self.get_cancel_deadline()


    def calc_total_cost(self) -> int:
        """Calculates the cost (date, related listing)"""
        nights = max((self.end_date - self.start_date).days, 1 if self.start_date == self.end_date else 0)
        price = getattr(self.listing, "price", 0)
        return nights * price

    def clean(self):
        check_booking_validations(self.listing)

    def save(self, *args, **kwargs):
        """Recalculates if this is a creation or dates/listing have changed, or update_fields is not set."""
        # self.full_clean(exclude=None)
        update_fields = kwargs.get("update_fields")
        checked = {"start_date", "end_date", "listing_id"}
        # Let's check if we need to recalculate total_cost?
        must_recalc = (not update_fields) or any(field in checked for field in (update_fields or ()))
        if must_recalc:
            self.total_cost = self.calc_total_cost()
            # for partial save — added total_cost in update_fields
            if update_fields is not None and "total_cost" not in update_fields:
                kwargs["update_fields"] = list(set(update_fields) | {"total_cost"})

        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.listing_id}: {self.start_date}-{self.end_date}, {self.status}, {self.total_cost}"
