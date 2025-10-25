import pytest
from faker import Faker
import random

from apps.core.users_seed_test import BASE_URL
from rental_api import RentalApi, create_listing_as_lessor, future_time, _login_renter, _login_admin, _login_lessor, \
    fake
from apps.core.enums import Roles, TypesHousing

@pytest.mark.integration
def test_create_listing_by_lessor():
    # lessor logs in and creates a listing
    start1, end1, days = future_time()
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=4,
    )

@pytest.mark.integration
def test_create_listing_by_renter_negative():
    # lessor logs in and creates a listing
    renter = _login_renter()
    user_r = renter.user()
    title = None
    code, body = renter.create_listing(user_r, title, True)
    assert code in (403, 404), body

@pytest.mark.integration
def test_create_listing_by_admin():
    # ADMIN logs in and creates a listing
    admin = _login_admin()
    user_a = admin.user()
    title = None
    code, body = admin.create_listing(user_a, title, True)
    assert code in (200, 201), body

@pytest.mark.integration
def test_list_listings_public():
    # Public List (anonymous): Waiting for 200 and list (ACTIVE only)
    anonymous = RentalApi(BASE_URL)
    page = anonymous.list_listings(search="apartment", ordering="-created_at", page_size=5)
    results = page.get("results", page)
    assert isinstance(results, list)

@pytest.mark.integration
def test_list_listings_owner():
    # Public List (anonymous): Waiting for 200 and list (ACTIVE only)
    anonymous = RentalApi(BASE_URL)
    page = anonymous.list_listings(ordering="-created_at")

    lessor = _login_lessor()
    user_l = lessor.user()
    title = None
    code, body = lessor.create_listing(user_l, title, True)
    page = lessor.list_listings(auth=True, ordering="-created_at")

    results = page.get("results", page)
    assert isinstance(results, list)


@pytest.mark.integration
def test_retrieve_active_listing_public():
    # Lessor creates an ACTIVE listing
    title = "Test_retrieve_active_listing_public"
    start1, end1, days = future_time()
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=4,
    )
    # Anonymous user can get ACTIVE by ID
    anonymous = RentalApi(BASE_URL)
    resp = anonymous.get_listing(listing_id)  # без токена
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == listing_id
    assert body["title"].startswith(title)

@pytest.mark.integration
def test_retrieve_inactive_listing_visibility():
    # Lessor creates an INACTIVE listing
    title = "Test_retrieve_inactive_listing_visibility"
    lessor = _login_lessor()
    user_l = lessor.user()
    status_code, created_listing = lessor.create_listing(user_l, title, False)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # anonymous should not see
    anonymous = RentalApi(BASE_URL)
    user_a = anonymous.get_listing(listing_id)
    assert user_a.status_code in (403, 404)
    # renter - should not see
    renter = _login_renter()
    user_r = renter.get_listing(listing_id)
    assert user_r.status_code in (403, 404)

    # owner - must see
    user_owner = lessor.get_listing(listing_id)
    assert user_owner.status_code == 200, user_owner.text
    assert user_owner.json()["id"] == listing_id


@pytest.mark.integration
def test_owner_can_put_listing():
    # lessor logs in and creates an ACTIVE listing
    lessor = _login_lessor()
    user_l = lessor.user()
    title = "Test_owner_can_put_listing"
    status_code, created_listing = lessor.create_listing(user_l, title)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # PUT from the Owner
    city = fake.city()
    street = fake.street_name()
    payload = {
        "title": f"{title} PUT {fake.word().capitalize()}",
        "description": fake.paragraph(nb_sentences=3),
        "location": f"{city}, {street}",
        "city": city,
        "country": "DE",
        "price": random.randint(300, 50_000),
        "rooms": random.randint(1, 20),
        "type": random.choice(TypesHousing.values),
        "is_active": False,
        "owner": created_listing.get("owner") # if owner is passed, it should be ignored (read_only)
    }
    resp_put = lessor.update_listing_put(listing_id, payload)
    assert resp_put.status_code in (200, 202), resp_put.text
    body = resp_put.json()
    assert body["title"].startswith(title + " PUT ")
    assert body["is_active"] == False

@pytest.mark.integration
def test_owner_can_patch_listing():
    # lessor logs in and creates an INACTIVE listing
    lessor = _login_lessor()
    user_l = lessor.user()
    title = "Test_owner_can_patch_listing"
    # lessor create listing with status is_activ=True
    status_code, created_listing = lessor.create_listing(user_l, title, True)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # Partial update (PATCH) -> status is_activ=False
    patch_payload = {"title": f"{title} PATCH {fake.word().capitalize()}", "is_active": False}
    resp_patch = lessor.update_listing_patch(listing_id, patch_payload)
    assert resp_patch.status_code in (200, 202), resp_patch.text
    body = resp_patch.json()
    assert body["title"].startswith(title + " PATCH ")
    assert body["is_active"] == False

@pytest.mark.integration
def test_update_forbidden_for_renter():
    # lessor logs in and creates an INACTIVE listing
    lessor = _login_lessor()
    user_l = lessor.user()
    title = "Test_update_forbidden_for_renter"
    status_code, created_listing = lessor.create_listing(user_l, title, True)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # renter logs in and tries to update
    # PUT
    renter = _login_renter()
    renter_put = renter.update_listing_put(listing_id, {
        "title": f"{title} Hack {fake.word().capitalize()}",
        "description": "???",
        "location": "...",
        "city": "...",
        "country": "00",
        "price": 100_000,
        "rooms": 99,
        "type": TypesHousing.STUDIO,
        "is_active": False,
    })
    assert renter_put.status_code in (403, 404)
    # PATCH
    renter_patch = renter.update_listing_patch(listing_id, {"is_active": False})
    assert renter_patch.status_code in (403, 404)
