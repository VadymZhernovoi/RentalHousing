from rest_framework import serializers

from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    # owner_id = serializers.UUIDField(source="owner.id", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_id = serializers.ReadOnlyField()

    class Meta:
        model = Listing
        fields = "__all__"
        read_only_fields = ("owner", "created_at", "updated_at")