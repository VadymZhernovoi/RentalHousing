import pytest
from faker import Faker
import random

from rental_api import RentalApi
from apps.core.enums import Roles, Types

BASE_URL = "http://localhost:8000/api/v1"
EMAIL_LESSOR = "user2@example.com"
PWD_LESSOR = "YourStrongPass2!"
EMAIL_RENTER = "user1@example.com"
PWD_RENTER = "YourStrongPass1!"
EMAIL_ADMIN = "admin@admin.com"
PWD_ADMIN = "Pa$$w0rd"

fake = Faker()

@pytest.mark.integration
def test_create_listing_by_lessor():
    # lessor logs in and creates a listing
    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
    user_l = lessor.user()
    assert user_l["role"] in (Roles.LESSOR, Roles.ADMIN)

    title = "Test_create_by_lessor"
    status_code, created_listing = lessor.create_listing(user_l, title)
    listing_id = created_listing.get("id") or created_listing.get("uuid")
    assert status_code in (200, 201) and listing_id, "The ID listing should return."

@pytest.mark.integration
def test_create_listing_by_renter_negative():
    # lessor logs in and creates a listing
    renter = RentalApi(BASE_URL)
    renter.login(EMAIL_RENTER, PWD_RENTER)
    user_r = renter.user()
    assert user_r["role"] in (Roles.RENTER, Roles.ADMIN)

    title = "Test_create_by_RENTER"
    status_code, created_listing = renter.create_listing(user_r, title)
    listing_id = created_listing.get("id") or created_listing.get("uuid")
    assert status_code in (403, 404) and listing_id == None, "The ID listing should not return."

@pytest.mark.integration
def test_create_listing_by_admin():
    # ADMIN logs in and creates a listing
    admin = RentalApi(BASE_URL)
    admin.login(EMAIL_ADMIN, PWD_ADMIN)
    user_a = admin.user()
    assert user_a["role"] == Roles.ADMIN

    title = "Test_create_by_ADMIN"
    status_code, created_listing = admin.create_listing(user_a, title)
    listing_id = created_listing.get("id") or created_listing.get("uuid")
    assert status_code in (200, 201) and listing_id, "The ID listing should return."


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

    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
    page = lessor.list_listings(auth=True, ordering="-created_at")

    results = page.get("results", page)
    assert isinstance(results, list)


@pytest.mark.integration
def test_retrieve_active_listing_public():
    # Lessor creates an ACTIVE listing
    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
    user_l = lessor.user()
    title = "Test_retrieve_active_listing_public"
    status_code, created_listing = lessor.create_listing(user_l, title)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

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
    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
    user_l = lessor.user()
    title = "Test_retrieve_inactive_listing_visibility"
    status_code, created_listing = lessor.create_listing(user_l, title, False)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # anonymous should not see
    anonymous = RentalApi(BASE_URL)
    user_a = anonymous.get_listing(listing_id)
    assert user_a.status_code in (403, 404)
    # renter - should not see
    renter = RentalApi(BASE_URL)
    renter.login(EMAIL_RENTER, PWD_RENTER)
    user_r = renter.get_listing(listing_id)
    assert user_r.status_code in (403, 404)

    # owner - must see
    user_owner = lessor.get_listing(listing_id)
    assert user_owner.status_code == 200, user_owner.text
    assert user_owner.json()["id"] == listing_id


@pytest.mark.integration
def test_owner_can_put_listing():
    # lessor logs in and creates an ACTIVE listing
    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
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
        "type": random.choice(Types.values),
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
    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
    user_l = lessor.user()
    title = "Test_owner_can_patch_listing"
    status_code, created_listing = lessor.create_listing(user_l, title, False)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # Partial update (PATCH)
    patch_payload = {"title": f"{title} PATCH {fake.word().capitalize()}", "is_active": False}
    resp_patch = lessor.update_listing_patch(listing_id, patch_payload)
    assert resp_patch.status_code in (200, 202), resp_patch.text
    body = resp_patch.json()
    assert body["title"].startswith(title + " PATCH ")
    assert body["is_active"] == True

@pytest.mark.integration
def test_update_forbidden_for_renter():
    # lessor logs in and creates an INACTIVE listing
    lessor = RentalApi(BASE_URL)
    lessor.login(EMAIL_LESSOR, PWD_LESSOR)
    user_l = lessor.user()
    title = "Test_update_forbidden_for_renter"
    status_code, created_listing = lessor.create_listing(user_l, title, False)
    listing_id = created_listing.get("id") or created_listing.get("uuid")

    # renter logs in and tries to update
    # PUT
    renter = RentalApi(BASE_URL)
    renter.login(EMAIL_RENTER, PWD_RENTER)
    renter_put = renter.update_listing_put(listing_id, {
        "title": f"{title} Hack {fake.word().capitalize()}",
        "description": "???",
        "location": "...",
        "city": "...",
        "country": "00",
        "price": 100_000,
        "rooms": 99,
        "type": Types.STUDIO,
        "is_active": False,
    })
    assert renter_put.status_code in (403, 404)
    # PATCH
    renter_patch = renter.update_listing_patch(listing_id, {"is_active": False})
    assert renter_patch.status_code in (403, 404)
