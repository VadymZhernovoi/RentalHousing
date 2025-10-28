import random
from faker import Faker

import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RentalHousing.settings')
django.setup()
from ..core.enums import TypesHousing
from .models import Listing
from django.contrib.auth import get_user_model


def create_listings():
    fake = Faker("de_DE")
    User = get_user_model()
    lessors = list(User.objects.filter(role="lessor"))
    if not lessors:
        raise RuntimeError("Not found lessor users")

    for _ in range(20):
        owner = random.choice(lessors)
        city = fake.city()
        street = fake.street_name()
        Listing.objects.create(
            owner=owner,
            title=f"{fake.word().capitalize()} Apartment",
            description=fake.paragraph(nb_sentences=3),
            location=f"{city}, {street}",
            city=city,
            country="DE",
            price=random.randint(300, 50_000),
            rooms=random.randint(1, 20),
            type_housing=random.choice(TypesHousing.values),
            is_active=random.choice([True, False]),
        )

if __name__ == "__main__":
    create_listings()