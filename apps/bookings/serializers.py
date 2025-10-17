from django.db.models.query_utils import Q
from rest_framework import serializers
from django.utils import timezone

from .models import Booking
from ..core.enums import StatusBooking

class BookingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ("id", "listing", "start_date", "end_date",
                  "guests", "baby_cribs", "kitchen_needed", "parking_needed", "pets",
                  "status",)
        read_only_fields = ("status",)

    def validate(self, attrs):
        listing = attrs.get("listing") or getattr(self.instance, "listing", None)
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))

        if not listing or not start or not end:
            return attrs
        if end <= start:
            raise serializers.ValidationError({"end_date": "end_date must be after start_date."})

        today = timezone.localdate()
        # intersection: start < e.end AND end > e.start
        overlap_qs = Booking.objects.filter(
            listing=listing, status=StatusBooking.APPROVED, end_date__gt=today
            ).filter(Q(start_date__lt=end) & Q(end_date__gt=start))
        # if this is an update, exclude the current entry
        if self.instance:
            overlap_qs = overlap_qs.exclude(pk=self.instance.pk)
        if overlap_qs.exists():
            raise serializers.ValidationError(
                {"non_field_errors": "Dates overlap with an approved booking that has not finished yet."}
            )
        # span_days_max: span_days_max=Null - 365 days
        span_days_max = listing.span_days_max if listing.span_days_max > 0 else 365
        if (end - start).days > span_days_max:
            raise serializers.ValidationError({
                "span_days":
                    f"Reservations cannot be made for a period longer than {span_days_max} days."
            })

        guests = attrs.get("guests", getattr(self.instance, "guests", 1))
        baby_cribs = attrs.get("baby_cribs", getattr(self.instance, "baby_cribs", 0))
        kitchen_needed = attrs.get("kitchen_needed", getattr(self.instance, "kitchen_needed", False))
        parking_needed = attrs.get("parking_needed", getattr(self.instance, "parking_needed", False))
        pets = attrs.get("pets", getattr(self.instance, "pets", False))


        errors = {}
        # Check
        # is_active
        if hasattr(listing, "is_active") and not listing.is_active:
            errors["listing"] = "Listing is inactive and cannot be booked."

        # Guests: max_guests=0 - no limit
        if listing.guests_max > 0 and guests > listing.guests_max:
            errors["guests"] = f"Guests exceed the listing limit (max: {listing.guests_max})."
        # Baby Cribs: max_baby_crib=0 — no limit
        if listing.baby_crib_max > 0 and baby_cribs > listing.baby_crib_max:
            errors["baby_cribs"] = f"Baby cribs exceed the listing limit (max: {listing.baby_crib_max})."
        # Kitchen
        if kitchen_needed and listing.has_kitchen is False:
            errors["kitchen_needed"] = "Kitchen is not available for this listing."
        # parking
        if parking_needed and listing.parking_available is False:
            errors["parking_needed"] = "Parking is not available for this listing."
        # pets
        if pets and listing.pets_possible is False:
            errors["pets"] = "Pets are not possible for this listing."
        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class BookingListSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    renter_email = serializers.ReadOnlyField(source="renter.email")
    total_cost = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "listing", "listing_title",
            "renter", "renter_email",
            "start_date", "end_date",
            "guests",
            "baby_cribs",
            "kitchen_needed",
            "created_at"
        )
        read_only_fields = ("status",)


class BookingCancelSerializer(serializers.Serializer):
    reason_cancel = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        booking = self.context["booking"]
        user = self.context["request"].user

        if not booking.is_can_be_cancellation():
            raise serializers.ValidationError(
                {"detail": f"Cancellation is not allowed. Deadline: {booking.get_cancel_deadline().isoformat()}"}
            )
        if booking.status not in (StatusBooking.PENDING, StatusBooking.APPROVED):
            raise serializers.ValidationError({"detail": f"Cannot cancel in {booking.status} status."})
        return attrs