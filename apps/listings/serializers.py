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

    def validate(self, attrs):
        owner = self.context["request"].user
        city = attrs.get("city", getattr(self.instance, "city", "")) or ""
        location = attrs.get("location", getattr(self.instance, "location", "")) or ""

        qs = Listing.objects.filter(owner=owner, city=city, location=location)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({
                "non_field_errors": ["Listing with the same (owner, city, location) already exists."]
            })
        return attrs