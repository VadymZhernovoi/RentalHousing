from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("listing", "author__username", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("listing__title", "author__email", "author__username", "comment")
    ordering = ("-created_at",)
    autocomplete_fields = ("listing", "author", "booking")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("listing", "booking", "author")}),
        ("Review", {"fields": ("rating", "comment")}),
        ("Meta", {"fields": ("created_at",)}),
    )


from django.contrib import admin

# Register your models here.
