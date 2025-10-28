from rest_framework.permissions import BasePermission, SAFE_METHODS

from .roles import is_lessor, is_moderator, is_admin, is_renter


class ListingCreatePermission(BasePermission):
    def has_permission(self, request, view):
        return is_lessor(request.user) or is_admin(request.user)


class ListingChangeDeletePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return is_admin(user) or (is_lessor(user) and obj.owner_id == user.id)


class BookingCreatePermission(BasePermission):
    def has_permission(self, request, view):
        return is_renter(request.user) or is_admin(request.user)


class BookingChangePermission(BasePermission):
    """
    Renter can change their own (except approve/decline), Moderator/Admin — change everything.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin(user) or is_moderator(user):
            return True

        return is_renter(user) and obj.renter_id == user.id


class BookingApproveDeclineCompletePermission(BasePermission):
    """
    Lessor can approve/decline only their own listings, Moderator/Admin — everything.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin(user) or is_moderator(user):
            return True

        return is_lessor(user) and obj.listing.owner_id == user.id


ROLE_PERMS = {
    "renter": [
        "listings.view_listing",
        "bookings.add_booking", "bookings.change_booking", "bookings.view_booking",
        "reviews.add_review", "reviews.change_review", "reviews.view_review",
    ],
    "lessor": [
        "listings.view_listing", "listings.add_listing", "listings.change_listing", "listings.delete_listing",
        "listings.view_inactive_listing", "listings.toggle_active_listing",
        "bookings.view_booking", "bookings.can_approve", "bookings.can_decline", "bookings.can_complete",
        "reviews.view_review", "reviews.owner_comment",
    ],
    "moderator": [
        "listings.view_listing", "listings.view_inactive_listing", "listings.view_all_listings",
        "bookings.view_booking",
        "reviews.view_review", "reviews.change_review", "reviews.moderate_review",
    ],
}