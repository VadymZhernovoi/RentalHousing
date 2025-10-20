from typing import Optional, Literal, Any
from django.contrib.auth import get_user_model

User = get_user_model()

def get_user_for(obj, kind):
    """
    Returns a user of the specified type from a Listing / Booking / Review object.
    kind:
    - "owner": Listing.owner / Booking.listing.owner
    - "lessor": Listing.owner
    - "renter": Booking.renter
    - "author": Review.author
    """
    if obj is None:
        return None

    if kind == "owner" or kind == "lessor":
        owner = getattr(obj, "owner", None) # Listing.owner
        if owner:
            return owner
        listing = getattr(obj, "listing", None) # Booking.listing.owner
        return getattr(listing, "owner", None)

    if kind == "renter":
        return getattr(obj, "renter", None) # Booking renter

    if kind == "author":
        return getattr(obj, "author", None) # Review author

    return None


def get_user_email(obj, kind) :
    """ Email user (owner/lessor/renter/author) or None. """
    user = get_user_for(obj, kind)
    if user is not None:
        return getattr(user, "email", None)
    else:
        return None


def get_ids_for_booking(booking) -> dict:
    """
    renter_id и lessor_id (owner).
    """
    renter_id = getattr(booking, "renter_id", None)
    lessor_id = getattr(getattr(booking, "listing", None), "owner_id", None)

    return {"renter_id": renter_id, "lessor_id": lessor_id}