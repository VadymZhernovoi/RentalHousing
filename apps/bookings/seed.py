import random
from faker import Faker
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RentalHousing.settings')
django.setup()
from django.contrib.auth import get_user_model
from django.db import transaction

from ..core.enums import StatusBooking, Roles
from ..listings.models import Listing
from ..bookings.models import Booking


def rng_seed(seed: int | None):
    if seed is None:
        return
    random.seed(seed)
    Faker.seed(seed)


def overlap(a_start: date, a_end: date, b_start: date, b_end: date):
    """Intersection of half-intervals (start, end)."""
    return a_start < b_end and b_start < a_end


def has_overlap(listing_id, start: date, end: date):
    """Only intersections with approved/pending (busy dates) are checked."""
    return Booking.objects.filter(
        listing_id=listing_id,
        status__in=[StatusBooking.APPROVED, StatusBooking.PENDING],
        start_date__lt=end,
        end_date__gt=start,
    ).exists()


def pick_free_date(listing_id, span_days: int, horizon_days: int, max_tries: int = 40):
    """ Picking a free date for a listing"""
    today = date.today()
    for _ in range(max_tries):
        start = today + timedelta(days=random.randint(1, horizon_days))
        end = start + timedelta(days=span_days)
        if not has_overlap(listing_id, start, end):
            return start, end
    return None, None


def choose_status():
    candidates = [StatusBooking.PENDING, StatusBooking.APPROVED, StatusBooking.DECLINED, StatusBooking.CANCELLED]
    return random.choice(candidates)


def create_bookings():
    rng_seed(args.seed)
    fake = Faker("de_DE")

    User = get_user_model()

    lessors = list(User.objects.filter(role=Roles, is_active=True))
    if not lessors:
        raise SystemExit("There are no users with the lessor role.")

    renters = list(User.objects.filter(role="renter", is_active=True))
    if not renters:
        raise SystemExit("There are no users with the renter role.")

    listings = list(Listing.objects.filter(owner__in=lessors, status="active"))
    if not listings:
        raise SystemExit("Lessors have no active listings.")

    created = 0
    with transaction.atomic():
        for _ in range(args.n):
            listing = random.choice(listings)
            renter = random.choice(renters)

            # It is not allowed to book your own advert.
            if renter.id == listing.owner_id:
                continue

            start, end = pick_free_date(listing.id, args.days, args.horizon)
            if start is None:
                continue  # no free date - skip

            guests = max(1, min(4, getattr(listing, "rooms", 1) or 1))
            status = choose_status()

            Booking.objects.create(
                listing=listing,
                renter=renter,
                start_date=start,
                end_date=end,
                guests=random.randint(1, guests),
                status=status,
            )
            created += 1

    print(f"Bookings created: {created}")


if __name__ == "__main__":
    create_bookings()