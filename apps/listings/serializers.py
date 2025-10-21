from rest_framework import serializers

from .models import Listing
from ..core.enums import Availability


class ListingSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_id = serializers.ReadOnlyField()
    has_kitchen = serializers.ChoiceField(choices=Availability.choices, required=False)
    parking_available = serializers.ChoiceField(choices=Availability.choices, required=False)
    pets_possible = serializers.ChoiceField(choices=Availability.choices, required=False)

    class Meta:
        model = Listing
        fields = "__all__"
        read_only_fields = ("owner", "created_at", "updated_at")