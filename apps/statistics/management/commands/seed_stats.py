import random
from typing import Iterable, Optional, Dict, Any
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.statistics.models import ListingView, SearchQuery
from apps.listings.models import Listing

User = get_user_model()

def seed_listing_views(n: int=100, users: Optional[Iterable[User]]=None) -> int:
    """
    Generate n random listing views (ListingView).
    """
    listings = list(Listing.objects.all().only("id"))
    if not listings:
        return 0
    users_list = list(users) if users is not None else list(User.objects.all().only("id"))
    list_views = []
    for _ in range(n):
        listing = random.choice(listings)
        user = random.choice(users_list) if users_list else None
        list_views.append(ListingView(listing=listing,user=user))
    created = len(ListingView.objects.bulk_create(list_views, batch_size=1000))
    return created


def seed_search_queries(n: int=100, users: Optional[Iterable[User]]=None) -> int:
    """
    Create n searches (SearchQuery).
    """
    cities = list(
        Listing.objects.exclude(city__isnull=True)
        .exclude(city__exact="")
        .values_list("city", flat=True)
        .distinct()[:20]
    )
    types = list(
        Listing.objects.exclude(type_housing__isnull=True)
        .exclude(type_housing__exact="")
        .values_list("type_housing", flat=True)
        .distinct()[:20]
    )
    users_list = list(users) if users is not None else list(User.objects.all().only("id"))
    list_searches = []
    for _ in range(n):
        keyword = random.choice(["luxury", "center", "metro", "park", "lake", "river"])
        params: Dict[str, Any] = {}
        if random.random() < 0.6:
            params["price_min"] = random.choice([30, 50, 80, 120])
        if random.random() < 0.6:
            params["price_max"] = random.choice([800, 1200, 1800, 3000])
        if random.random() < 0.4:
            params["rooms_min"] = random.randint(1, 3)
        if random.random() < 0.4:
            params["rooms_max"] = random.randint(5, 10)
        if random.random() < 0.4:
            params["guests"] = random.randint(1, 10)
        if random.random() < 0.5 and cities:
            params["city"] = random.choice(cities)
        if random.random() < 0.3 and types:
            params["type_housing"] = random.choice(types)
        if random.random() < 0.3 and types:
            params["baby_crib"] = random.randint(1, 3)
        if random.random() < 0.3:
            params["has_kitchen"] = random.choice([True, False])
        if random.random() < 0.3:
            params["parking_available"] = random.choice([True, False])
        if random.random() < 0.2:
            params["pets_possible"] = random.choice([True, False])

        list_searches.append(
            SearchQuery(
                user=random.choice(users_list) if users_list else None,
                keywords=keyword,
                params=params,
            )
        )
    created = len(SearchQuery.objects.bulk_create(list_searches, batch_size=500))
    return created


class Command(BaseCommand):
    help = "Created ListingView + SearchQuery."

    @transaction.atomic
    def handle(self, *args, **opts):
        n_searches = 100 # number of views
        n_views = 120    # number of searches

        users = list(User.objects.all().only("id")[:200])

        created_views = created_queries = 0
        created_views = seed_listing_views(n=n_views, users=users)
        self.stdout.write(self.style.SUCCESS(f"[views] created: {created_views}"))

        created_queries = seed_search_queries(n=n_searches, users=users)
        self.stdout.write(self.style.SUCCESS(f"[searches] created: {created_queries}"))

        self.stdout.write(self.style.SUCCESS("Done."))