from rest_framework import serializers

from .models import SearchQueryStats, SearchQuery

class SearchQueryStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQueryStats
        fields = ("id", "keywords", "count", "updated_at")
        read_only_fields = fields

class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ("id", "user", "session_id", "keywords", "params", "created_at")
        read_only_fields = fields