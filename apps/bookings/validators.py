from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models.query_utils import Q
from typing import TYPE_CHECKING
from django.apps import apps

from ..core.enums import StatusBooking

if TYPE_CHECKING:
    from .models import Booking  # noqa: F401

def _BookingModel():
    """Ленивое получение модели Booking без импортов на уровне модуля."""
    return apps.get_model("bookings", "Booking")

def validate_listing_active(booking):
    if getattr(booking.listing, "is_active", True) is False:
        raise ValidationError({"listing": f"Listing {booking.listing_id} is inactive and cannot be booked."})

def validate_overlap_approved(booking):
    """
    Disallow bookings if there is an APPROVED booking for this listing,
    which is not yet closed and has overlapping dates.
    Occurrence condition: existing.start < new_end AND existing.end > new_start
    """
    if not booking.listing or not booking.start_date or not booking.end_date:
        return

    today = timezone.localdate()

    Booking = _BookingModel()
    queryset = (Booking.objects
                .filter(listing=booking.listing, status=StatusBooking.APPROVED.value, end_date__gt=today)
                .filter(Q(start_date__lt=booking.end_date) & Q(end_date__gt=booking.start_date))
                .exclude(pk=booking.pk)
                )
    # if getattr(booking, "pk", None):
    #     queryset = queryset.exclude(pk=booking.pk)

    if queryset.exists():
        raise ValidationError({"non_field_errors": "Dates overlap with an approved booking that has not finished yet."})

def validate_dates(booking):
    if booking.end <= booking.start:
        raise ValidationError(
            {"end_date": f"end_date ({booking.end.isoformat()}) must be after start date ({booking.start.isoformat()})."})

    today = timezone.localdate()
    if booking.start < today:
        raise ValidationError(
            {"start_date": f"The booking start date ({booking.start.isoformat()}) must be in the future."})


def validate_capacity(booking):
    guests_max = int(getattr(booking.listing, "guests_max", 0) or 0)
    if 0 < guests_max < booking.guests:
        raise ValidationError({"guests": f"Guests exceed the listing limit (max: {guests_max})."})

    baby_crib_max = int(getattr(booking.listing, "baby_crib_max", 0) or 0)
    if 0 < baby_crib_max < booking.baby_cribs:
        raise ValidationError({"baby_cribs": f"Baby cribs exceed the listing limit (max: {baby_crib_max})."})

def validate_facilities(booking):
    from apps.listings.models import Availability
    if getattr(booking, "kitchen_needed", False) and getattr(booking.listing, "has_kitchen", None) == Availability.NO:
        raise ValidationError({"kitchen_needed": "Kitchen is not available for this listing."})

    if getattr(booking, "parking_needed", False) and getattr(booking.listing, "parking_available", None) == Availability.NO:
        raise ValidationError({"parking_needed": "Parking is not available for this listing."})

    if getattr(booking, "pets", False) and getattr(booking.listing, "pets_possible", None) == Availability.NO:
        raise ValidationError({"pets": "Pets is not possible for this listing."})

def validate_span_limits(booking, *, default_max_days: int = 365):
    """
    Checking the reservation duration.
    - span_days_min: If >0, check that span >= min
    - span_days_max: If >0, check that span <= max; otherwise, use default_max_days
    """
    if not booking.start_date or not booking.end_date:
        return
    span = (booking.end_date - booking.start_date).days
    # Normalize min/max
    try:
        span_days_min = int(getattr(booking.listing, "span_days_min", 0) or 0)
    except (TypeError, ValueError):
        span_days_min = 0
    try:
        raw_max = getattr(booking.listing, "span_days_max", 0)
        span_days_max = int(raw_max or 0)
    except (TypeError, ValueError):
        span_days_max = 0
    # max: if not specified or <=0, use the default settings 365
    effective_max = span_days_max if span_days_max > 0 else int(default_max_days)
    # check min, if given
    if span_days_min > 0 and span < span_days_min:
        raise ValidationError(
            {"span_days": f"Reservation must be at least {span_days_min} nights."}
        )
    # check span for effective_max
    if span > effective_max:
        limit = span_days_max if span_days_max > 0 else default_max_days
        raise ValidationError(
            {"span_days": f"Reservations cannot exceed {limit} nights."}
        )

def validate_minmax_span( booking):
    span = (booking.end_date - booking.start_date).days
    span_days_min = int(getattr(booking.listing, "span_days_min", 0) or 0)
    span_days_max = int(getattr(booking.listing, "span_days_max", 0) or 0)
    if span_days_min > 0 and span < span_days_min:
        raise ValidationError({"span_days": f"Reservation must be at least {span_days_min} nights."})
    if 0 < span_days_max < span:
        raise ValidationError({"span_days": f"Reservations cannot exceed {span_days_max} nights."})


def validate_owner_not_self(booking):
    # The owner cannot reserve his listing
    if getattr(booking, "renter_id", None) and getattr(booking.listing, "owner_id", None) and booking.renter_id == booking.listing.owner_id:
        raise ValidationError({"booking": "Owner cannot book their own listing."})

def validate_counts_positive(booking):
    if booking.guests is None or booking.guests < 1:
        raise ValidationError({"guests": "Guests must be >= 1."})
    if booking.baby_cribs is None or booking.baby_cribs < 0:
        raise ValidationError({"baby_cribs": "Baby cribs must be >= 0."})
    
def check_booking_validations(booking):
    """All checks."""
    validate_owner_not_self(booking)
    validate_listing_active(booking)
    validate_dates(booking)
    validate_span_limits(booking)
    validate_minmax_span(booking)
    validate_overlap_approved(booking)
    validate_capacity(booking)
    validate_facilities(booking)
    validate_counts_positive(booking)