from django.contrib import admin

from .models import ListingView, SearchQuery, SearchQueryStats, ListingStats


@admin.register(ListingView)
class ListingViewAdmin(admin.ModelAdmin):
    list_display = ("listing", "user", "session_id", "created_at")
    search_fields = ("listing__title", "user__email", "session_id")
    list_filter = ("created_at",)


@admin.register(SearchQuery, SearchQueryStats)
class _InlineAdmin(admin.ModelAdmin):
    list_display = ("keywords", "created_at") if hasattr(SearchQuery, "keywords") else ("keywords", "count", "updated_at")
    search_fields = ("keywords",)


@admin.register(ListingStats)
class ListingStatsAdmin(admin.ModelAdmin):
    list_display = ("listing", "views_count", "reviews_count", "avg_rating", "updated_at")
    search_fields = ("listing__title",)


