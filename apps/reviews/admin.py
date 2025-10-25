from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("listing", "author__username", "rating", "created_at", "is_valid")
    list_filter = ("rating", "created_at")
    search_fields = ("listing__title", "author__email", "author__username", "comment", "owner_comment", "is_valid")
    ordering = ("-created_at",)
    autocomplete_fields = ("listing", "author", "booking")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("listing", "booking", "author", "is_valid")}),
        ("Review", {"fields": ("rating", "comment", "owner_comment")}),
        ("Meta", {"fields": ("created_at",)}),
    )

