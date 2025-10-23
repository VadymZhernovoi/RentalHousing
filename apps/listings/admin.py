from django.contrib import admin, messages

from .models import Listing
from ..bookings.models import Booking
from ..reviews.models import Review


@admin.action(description="Make selected ACTIVE")
def make_active(modeladmin, request, queryset):
    updated = queryset.exclude(is_active=True).update(is_active=True)
    if updated:
        messages.success(request, f"Set to ACTIVE: {updated}")
    else:
        messages.info(request, "All selected ones are already in ACTIVE")


@admin.action(description="Make selected INACTIVE")
def make_inactive(modeladmin, request, queryset):
    updated = queryset.exclude(is_active=False).update(is_active=False)
    if updated:
        messages.success(request, f"Set to INACTIVE: {updated}")
    else:
        messages.info(request, "All selected ones are already in INACTIVE")


@admin.action(description="Switch status ACTIVE/INACTIVE")
def toggle_status(modeladmin, request, queryset):
    made_active = queryset.filter(is_active=False).update(is_active=True)
    made_inactive = queryset.filter(is_active=True).update(is_active=False)
    total = made_active + made_inactive
    if total:
        messages.success(
            request,
            f"The status of {total} has changed (ACTIVE->{made_inactive}, INACTIVE->{made_active})"
        )
    else:
        messages.info(
            request,
            "There is nothing to switch (there is no ACTIVE/INACTIVE among the selected ones)"
        )


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ("renter", "start_date", "end_date",
              "guests", "baby_cribs", "kitchen_needed", "parking_needed", "pets",
              "status", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("renter",)  # AJAX search
    show_change_link = True


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ("author", "rating", "comment", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",) # AJAX search
    show_change_link = True


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title",
                    "owner", "city", "price", "span_days_max", "span_days_min",
                    "guests_max", "baby_cribs_max", "has_kitchen", "parking_available", "pets_possible",
                    "created_at", "views_count", "reviews_count", "avg_rating")
    list_filter = ("is_active", "type_housing", "city", "created_at", "baby_cribs_max", "has_kitchen", "parking_available")
    search_fields = ("title", "description", "city", "owner__email", "owner__username")
    ordering = ("-created_at",)
    autocomplete_fields = ("owner",)  # AJAX search
    readonly_fields = ("created_at", "updated_at", "views_count", "reviews_count", "avg_rating",)
    fieldsets = (
        (None, {"fields": ("title", "description")}),
        ("Location", {"fields": ("location", "city", "country")}),
        ("Details", {"fields": ("price", "rooms", "guests_max", "span_days_max", "span_days_min",
                                "baby_cribs_max", "has_kitchen", "parking_available", "pets_possible",
                                "type_housing", "is_active")}),
        ("Statistics", {"fields": ("views_count", "reviews_count", "avg_rating")}),
        ("Owner", {"fields": ("owner",)}),
        ("Meta", {"fields": ("created_at", "updated_at")}),
    )
    actions = [make_active, make_inactive, toggle_status]
    inlines = [BookingInline, ReviewInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("listing_stats", "owner")

    @admin.display(ordering="listing_stats__views_count", description="Views")
    def views_count(self, obj):
        return getattr(getattr(obj, "listing_stats", None), "views_count", 0)

    @admin.display(ordering="listing_stats__reviews_count", description="Reviews")
    def reviews_count(self, obj):
        return getattr(getattr(obj, "listing_stats", None), "reviews_count", 0)

    @admin.display(ordering="listing_stats__avg_rating", description="Rating")
    def avg_rating(self, obj):
        val = getattr(getattr(obj, "listing_stats", None), "avg_rating", 0) or 0
        return f"{float(val):.2f}"

