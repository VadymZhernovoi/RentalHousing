from rest_framework import serializers

from .models import Booking
from ..core.enums import StatusBooking, Availability
from .validators import check_booking_validations

class BookingCreateUpdateSerializer(serializers.ModelSerializer):
    kitchen_needed = serializers.ChoiceField(choices=Availability.choices, required=False)
    parking_needed = serializers.ChoiceField(choices=Availability.choices, required=False)
    pets = serializers.ChoiceField(choices=Availability.choices, required=False)

    class Meta:
        model = Booking
        fields = ("id", "listing", "start_date", "end_date",
                  "guests", "baby_cribs", "kitchen_needed", "parking_needed", "pets",
                  "status",)
        read_only_fields = ("status",)

    def validate(self, attrs):
        listing = attrs.get("listing") or getattr(self.instance, "listing", None)
        if not listing:
            return attrs

        instance = Booking(
            listing=attrs.get("listing") or getattr(self.instance, "listing", None),
            start_date=attrs.get("start_date", getattr(self.instance, "start_date", None)),
            end_date=attrs.get("end_date", getattr(self.instance, "end_date", None)),
            guests=attrs.get("guests", getattr(self.instance, "guests", 1)),
            baby_cribs=attrs.get("baby_cribs", getattr(self.instance, "baby_cribs", 0)),
            kitchen_needed=attrs.get("kitchen_needed", getattr(self.instance, "kitchen_needed", False)),
            parking_needed=attrs.get("parking_needed", getattr(self.instance, "parking_needed", False)),
            pets=attrs.get("pets", getattr(self.instance, "pets", False)),
        )
        # use model validators
        check_booking_validations(instance)

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