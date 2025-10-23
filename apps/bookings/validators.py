from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models.query_utils import Q
from typing import TYPE_CHECKING, Any
from django.apps import apps

from RentalHousing.settings import DEFAULT_SPAN_DAYS_MAX
from ..core.enums import StatusBooking

if TYPE_CHECKING:
    from .models import Booking  # noqa: F401

def _BookingModel():
    """Lazy fetching of Booking model without imports."""
    return apps.get_model("bookings", "Booking")

def validate_listing_active(booking: Any):
    if getattr(booking.listing, "is_active", True) is False:
        raise ValidationError({"listing": f"Listing {booking.listing_id} is inactive and cannot be booked."})

def validate_overlap_approved(booking: Any):
    """
    Disallow bookings if there is an APPROVED booking for this listing,
    which is not yet closed and has overlapping dates.
    Occurrence condition: existing.start_date < new_end AND existing.end_date > new_start
    """
    if not booking.listing or not booking.start_date or not booking.end_date:
        return

    today = timezone.localdate()

    Booking = _BookingModel()
    queryset = (Booking.objects
                .filter(listing=booking.listing, status=StatusBooking.APPROVED.value, end_date__gt=today)
                .filter(Q(start_date__lt=booking.end_date) & Q(end_date__gt=booking.start_date))
                )
    if getattr(booking, "pk", None):
        queryset = queryset.exclude(pk=booking.pk)

    if queryset.exists():
        raise ValidationError({"non_field_errors": "Dates overlap with an approved booking that has not finished yet."})

def validate_dates(booking: Any):
    if booking.end_date <= booking.start_date:
        raise ValidationError(
            {"end_date":
            f"end_date ({booking.end_date.isoformat()}) must be after start date ({booking.start_date.isoformat()})."}
        )

    today = timezone.localdate()
    if booking.start_date < today:
        raise ValidationError(
            {"start_date": f"The booking start date ({booking.start_date.isoformat()}) must be in the future."})

def validate_guests(booking: Any):
    guests_max = int(getattr(booking.listing, "guests_max", 0) or 0)
    if 0 < guests_max < booking.guests:
        raise ValidationError({"guests": f"Guests exceed the listing limit (max: {guests_max})."})

def validate_baby_crib(booking: Any):
    baby_cribs_max = int(getattr(booking.listing, "baby_cribs_max", 0) or 0)
    if 0 < baby_cribs_max < booking.baby_cribs:
        raise ValidationError({"baby_cribs": f"Baby cribs exceed the listing limit (max: {baby_cribs_max})."})

def validate_kitchen(booking: Any):
    from apps.listings.models import Availability
    if booking.kitchen_needed == Availability.YES and getattr(booking.listing, "has_kitchen", None) == Availability.NO:
        raise ValidationError({"kitchen_needed": "Kitchen is not available for this listing."})

def validate_parking(booking: Any):
    from apps.listings.models import Availability
    if (booking.parking_needed == Availability.YES and
        getattr(booking.listing, "parking_available", None) == Availability.NO):
        raise ValidationError({"parking_needed": "Parking is not available for this listing."})

def validate_pets(booking: Any):
    from apps.listings.models import Availability
    if booking.pets == Availability.YES and getattr(booking.listing, "pets_possible", None) == Availability.NO:
        raise ValidationError({"pets": "Pets is not possible for this listing."})

def validate_min_span(booking: Any):
    if not booking.start_date or not booking.end_date:
        return
    span = (booking.end_date - booking.start_date).days
    span_days_min = int(getattr(booking.listing, "span_days_min", 0) or 0)
    if span_days_min > 0 and span < span_days_min:
        raise ValidationError({"span_days": f"Reservation must be at least {span_days_min} nights."})

def validate_max_span(booking: Any):
    if not booking.start_date or not booking.end_date:
        return
    span = (booking.end_date - booking.start_date).days
    span_days_max = int(getattr(booking.listing, "span_days_max", DEFAULT_SPAN_DAYS_MAX) or DEFAULT_SPAN_DAYS_MAX)
    if 0 < span_days_max < span:
        raise ValidationError({"span_days": f"Reservations cannot exceed {span_days_max} nights."})

def validate_owner_not_self(booking: Any):
    # The owner cannot reserve his listing
    if (getattr(booking, "renter_id", None) and
        getattr(booking.listing, "owner_id", None) and booking.renter_id == booking.listing.owner_id):
        raise ValidationError({"booking": "Owner cannot book their own listing."})

def validate_guests_positive(booking: Any):
    if booking.guests is None or booking.guests < 1:
        raise ValidationError({"guests": "Guests must be >= 1."})

def validate_baby_cribs_positive(booking: Any):
    if booking.baby_cribs is None or booking.baby_cribs < 0:
        raise ValidationError({"baby_cribs": "Baby cribs must be >= 0."})
    
def check_booking_validations(booking: Any):
    """All checks."""
    validate_owner_not_self(booking)
    validate_listing_active(booking)
    validate_dates(booking)
    validate_min_span(booking)
    validate_max_span(booking)
    validate_overlap_approved(booking)
    validate_guests(booking)
    validate_baby_crib(booking)
    validate_kitchen(booking)
    validate_parking(booking)
    validate_pets(booking)
    validate_guests_positive(booking)
    validate_baby_cribs_positive(booking)