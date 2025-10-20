from django.db.models.query_utils import Q
from rest_framework import serializers
from django.utils import timezone

from .models import Review
from ..bookings.models import Booking
from ..core.enums import StatusBooking


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    listing = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ("id", "booking", "listing", "rating", "comment", "created_at", "author")
        read_only_fields = ("created_at", "listing")

    def get_fields(self):
        """
        Override serializer fields to restrict the selectable value for the "booking" field to completed bookings only.
        Logic:
        - Regular users: only their own bookings with status "completed".
        - Admins: any booking with status "completed".
        Uses the current request from self.context["request"] to determine the acting user.
        """
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)

        today = timezone.now().date()
        queryset = Booking.objects.filter(
            Q(status=StatusBooking.COMPLETED) | Q(end_date__lte=today)).select_related("listing")

        # admin can select any completed items; a non-admin can select only their own completed items.
        if not (user and user.is_authenticated and getattr(user, "role", None) == "admin"):
            if user and user.is_authenticated:
                queryset = queryset.filter(renter_id=user.id)
            else:
                queryset = Booking.objects.none()  # anonymous user cannot create anything.

        fields["booking"].queryset = queryset

        return fields

    def validate(self, attrs):
        user = self.context["request"].user.email
        user_id = self.context["request"].user.id
        booking = attrs["booking"]
        # only the renter of this booking
        if booking.renter_id != user_id:
            raise serializers.ValidationError({
                "review": [f"User {user} cannot create a review for a booking that is not theirs."]
            })
        # listing owner cannot leave a review on their listing.
        if booking.listing.owner_id == user_id:
            raise serializers.ValidationError({
                "review": [f"User {user} cannot create a review for their listing."]
            })
        # review can be created only after completion or after the departure date (end_date)
        today = timezone.now().date()
        is_completed = (booking.status == StatusBooking.COMPLETED)
        checkout_passed = (booking.end_date <= today)

        if not (is_completed or checkout_passed):
            raise serializers.ValidationError({
                "review": [f"A review can only be left after the booking is completed (booking: {booking.status}) "
                           f"or after the departure date ({booking.end_date})"]
            })

        return attrs

    def create(self, validated_data):
        """
        Auto-substitution listing from booking
        :param validated_data:
        :return:
        """
        validated_data["listing"] = validated_data["booking"].listing

        return super().create(validated_data)
