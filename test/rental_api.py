import requests
from typing import Any
from faker import Faker
import random
from datetime import date, timedelta

from apps.bookings.models import Booking
from apps.core.enums import TypesHousing, Availability

fake = Faker()

# BASE_URL     = "http://localhost:8000/api/v1"  # поправь при необходимости
# EMAIL_LESSOR = "lessor1@example.com"
# PWD_LESSOR   = "YourStrongPass1!"
# EMAIL_RENTER = "renter1@example.com"
# PWD_RENTER   = "YourStrongPass1!"
# EMAIL_MOD    = "moderator1@example.com"
# PWD_MOD      = "YourStrongPass1!"

class RentalApi:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.sess = requests.Session()

    # AUTH
    def login(self, email: str, password: str):
        """cookie access_token/refresh_token in self.sess.cookies"""
        resp = self.sess.post(f"{self.base_url}/user/login/", json={"email": email, "password": password},
                           allow_redirects=False)
        # print("LOGIN status:", resp.status_code)
        # print("SET-COOKIE header:", resp.headers.get("Set-Cookie"))
        # print("CookieJar get_dict():", self.sess.cookies.get_dict())
        # for c in self.sess.cookies:
        #     print("COOKIE:", c.name, c.value, "path=", c.path, "domain=", c.domain)
        assert resp.status_code == 200, resp.text
        return True

    # USERS
    def user(self):
        resp = self.sess.get(f"{self.base_url}/user/me/")  # cookies will go automatically
        assert resp.status_code == 200, resp.text
        return resp.json()

    def list_listings(self, **params):
        resp = self.sess.get(f"{self.base_url}/listings/", params=params or {})
        assert resp.status_code == 200, resp.text
        return resp.json()

    def get_listing(self, listing_id):
        resp = self.sess.get(f"{self.base_url}/listings/{listing_id}/")
        return resp  # вернём Response, чтобы можно было проверять 200/403/404


    # def _auth_headers(self):
    #     assert self.access, "Call login() first to set access token"
    #     return {"Authorization": f"Bearer {self.access}"}


    # LISTINGS
    def create_listing(self, owner, title: str, is_active: bool = True, **kwargs):
        """Create an listing (lessor/admin required)."""
        guests_max = kwargs.get("quests_max", random.randint(1, 10))
        baby_cribs_max = kwargs.get("baby_cribs_max", random.randint(1, 3))
        has_kitchen = kwargs.get("has_kitchen", random.choice(Availability.values))
        parking_available = kwargs.get("parking_available", random.choice(Availability.values))
        pets_possible = kwargs.get("pets_possible", random.choice(Availability.values))
        span_days_max = kwargs.get("span_days_max", random.randint(8, 90))
        span_days_min = kwargs.get("span_days_min", random.randint(0, 7))

        city = fake.city()
        street = fake.street_name()
        payload = {
            "owner": owner["id"],
            "title": f"{title} {fake.word().capitalize()}",
            "description": fake.paragraph(nb_sentences=3),
            "location": f"{city}, {street}",
            "city": city,
            "country": "DE",
            "price": random.randint(50, 5_000),
            "rooms": random.randint(1, 20),
            "span_days_max": span_days_max,
            "span_days_min": span_days_min,
            "guests_max": guests_max,
            "baby_cribs_max": baby_cribs_max,
            "has_kitchen": has_kitchen,
            "parking_available": parking_available,
            "pets_possible": pets_possible,
            "type": random.choice(TypesHousing.values),
            "is_active": is_active,
        }
        resp = self.sess.post(f"{self.base_url}/listings/", json=payload)
        return resp.status_code, resp.json()


    def update_listing_put(self, listing_id, payload: dict):
        resp = self.sess.put(f"{self.base_url}/listings/{listing_id}/", json=payload)
        return resp

    def update_listing_patch(self, listing_id, payload: dict):
        resp = self.sess.patch(f"{self.base_url}/listings/{listing_id}/", json=payload)
        return resp

    # BOOKINGS
    def create_booking(self, payload: dict):
        """Create booking (renter). payload: listing, start_date, end_date, guests"""
        resp = self.sess.post(f"{self.base_url}/bookings/",json=payload)
        assert resp.status_code in (200, 201), resp.text
        # booking_id = resp["id"]
        # return booking_id
        return resp.json()

    def approve_booking(self, booking_id):
        """Confirm booking (lessor - listing owner)."""
        resp = self.sess.post(f"{self.base_url}/bookings/{booking_id}/approve/")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def decline_booking(self, booking_id):
        """Decline booking (lessor - listing owner)."""
        resp = self.sess.post(f"{self.base_url}/bookings/{booking_id}/decline/" )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def list_bookings(self, params: dict | None = None):
        resp = self.sess.get(f"{self.base_url}/bookings/", params=params or {})
        assert resp.status_code == 200, resp.text
        return resp.json()

    def get_booking(self, booking_id):
        resp = self.sess.get(f"{self.base_url}/bookings/{booking_id}/")
        return resp  # Let's return a Response to differentiate between 200/403/404

    def cancel_booking(self, booking_id):
        resp = self.sess.post(f"{self.base_url}/bookings/{booking_id}/cancelled/")
        return resp

    # REVIEWS
    def create_review(self, booking_id, rating: int, comment: str):
        payload = {"booking": str(booking_id), "rating": rating, "comment": comment}
        resp = self.sess.post(
            f"{self.base_url}/reviews/",json=payload)
        assert resp.status_code in (200, 201, 400), resp.text
        return resp.json()

    def list_reviews(self, listing_id):
        resp = self.sess.get(f"{self.base_url}/reviews/", params={"listing": str(listing_id)})
        assert resp.status_code == 200, resp.text
        return resp.json()

    def owner_comment_review(self, review_id: str, text: str):
        return self.sess.post(f"{self.base_url}/reviews/{review_id}/owner-comment/",
                              json={"owner_comment": text})

    def moderate_review(self, review_id: str, is_valid: bool):
        return self.sess.post(f"{self.base_url}/reviews/{review_id}/moderate-validate/",
                              json={"is_valid": is_valid})

# def future_range(days=3, offset=10):
#     start = date.today() + timedelta(days=offset)
#     end   = start + timedelta(days=days)
#     return str(start), str(end)
#
# def create_listing_as_lessor(title="API Test Listing", *args, **kwargs) -> RentalApi:
#     lessor = RentalApi(BASE_URL)
#     lessor.login(EMAIL_LESSOR, PWD_LESSOR)
#     user_l = lessor.user()
#     code, body = lessor.create_listing(user_l, title, True, **kwargs)
#     assert code in (200, 201), body
#     return lessor, body["id"]
#
# def create_pending_booking(renter_api: RentalApi, listing_id: str, start: str, end: str, **kwargs: Any) -> Booking:
#     payload = {"listing": str(listing_id), "start_date": start, "end_date": end}
#     guests = kwargs.get("guests")
#     if guests is not None:
#         payload["guests"] = guests
#     baby_cribs = kwargs.get("baby_cribs")
#     if baby_cribs is not None:
#         payload["baby_cribs"] = baby_cribs
#     for key in ("kitchen_needed", "parking_needed", "pets"):
#         val = kwargs.get(key)
#         if val is not None:
#             payload[key] = val
#
#     bk = renter_api.create_booking(payload)
#     # return bk, status_code
#     assert bk["status"] in ("pending", "awaiting_payment", "pending"), bk
#     return bk.get("id", None)
