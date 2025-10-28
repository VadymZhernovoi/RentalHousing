from django.contrib import admin, messages
from django.utils import timezone

from .models import Booking
from ..core.enums import StatusBooking


def overlaps(qs, booking):
    """
    Are there any overlaps between booking and already approved ones in the database (except for itself).
    """
    return qs.filter(
        listing=booking.listing,
        status=StatusBooking.APPROVED,
        start_date__lt=booking.end_date,
        end_date__gt=booking.start_date
    ).exclude(pk=booking.pk).exists()

@admin.action(description="Mark selected as APPROVE")
def approve_bookings(modeladmin, request, queryset):
    ok, skipped = 0, 0
    for booking in queryset.select_related("listing"):
        if booking.status != StatusBooking.PENDING:
            skipped += 1
            continue
        if overlaps(Booking.objects, booking):
            messages.warning(request, f"Date intersection: booking #{booking.pk} for {booking.listing}")
            skipped += 1
            continue
        booking.status = StatusBooking.APPROVED
        booking.save(update_fields=["status"])
        ok += 1
    if ok:
        messages.success(request, f"Approved: {ok}")
    if skipped:
        messages.info(request, f"Skipped: {skipped}")

@admin.action(description="Mark selected as DECLINE")
def decline_bookings(modeladmin, request, queryset):
    changed = queryset.filter(status=StatusBooking.PENDING).update(status=StatusBooking.DECLINED)
    if changed:
        messages.success(request, f"Declined: {changed}")
    rest = queryset.count() - changed
    if rest:
        messages.info(request, f"Skipped (not pending): {rest}")

@admin.action(description="Mark selected as COMPLETED")
def complete_bookings(modeladmin, request, queryset):
    today = timezone.now().date()
    ok, skipped = 0, 0
    for booking in queryset:
        if booking.status != StatusBooking.APPROVED or booking.end_date > today:
            skipped += 1
            continue
        booking.status = StatusBooking.COMPLETED
        booking.save(update_fields=["status"])
        ok += 1
    if ok:
        messages.success(request, f"Completed: {ok}")
    if skipped:
        messages.info(request, f"Skipped (not approved or future end_date): {skipped}")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id",  "listing", "renter", "start_date", "end_date",
                    "guests", "baby_cribs", "kitchen_needed", "parking_needed", "pets", "total_cost", "created_at")
    list_filter = ("status", "created_at", "start_date", "end_date")
    search_fields = ("listing__title", "renter__email", "renter__username")
    ordering = ("-created_at",)
    autocomplete_fields = ("listing", "renter")
    date_hierarchy = "start_date"
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("listing", "renter")}),
        ("Dates", {"fields": ("start_date", "end_date", "total_cost")}),
        ("Details", {"fields": ("guests",  "baby_cribs", "kitchen_needed", "parking_needed", "pets", "status")}),
        ("Meta", {"fields": ("created_at",)}),
    )

    actions = [approve_bookings, decline_bookings, complete_bookings]
