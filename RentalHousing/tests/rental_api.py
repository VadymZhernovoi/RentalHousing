import requests
from faker import Faker
import random

from apps.core.enums import Types

fake = Faker()

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


    def _auth_headers(self):
        assert self.access, "Call login() first to set access token"
        return {"Authorization": f"Bearer {self.access}"}


    # LISTINGS
    def create_listing(self, owner, title: str, is_active: bool = True):
        """Create an listing (lessor/admin required)."""
        city = fake.city()
        street = fake.street_name()
        payload = {
            "owner": owner["id"],
            "title": f"{title} {fake.word().capitalize()}",
            "description": fake.paragraph(nb_sentences=3),
            "location": f"{city}, {street}",
            "city": city,
            "country": "DE",
            "price": random.randint(300, 50_000),
            "rooms": random.randint(1, 20),
            "type": random.choice(Types.values),
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
        resp = self.sess.post(
            f"{self.base_url}/bookings/",
            json=payload,
            headers=self._auth_headers(),
        )
        assert resp.status_code in (200, 201), resp.text
        return resp.json()

    def approve_booking(self, booking_id):
        """Confirm booking (lessor - listing owner)."""
        resp = self.sess.post(
            f"{self.base_url}/bookings/{booking_id}/approve/",
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def decline_booking(self, booking_id):
        """Decline booking (lessor - listing owner)."""
        resp = self.sess.post(
            f"{self.base_url}/bookings/{booking_id}/decline/",
            headers=self._auth_headers(),
        )
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
        resp = self.sess.post(f"{self.base_url}/bookings/{booking_id}/cancel/")
        return resp

    # REVIEWS
    def create_review(self, booking_id, rating: int, comment: str):
        payload = {"booking": str(booking_id), "rating": rating, "comment": comment}
        resp = self.sess.post(
            f"{self.base_url}/reviews/",
            json=payload,
            headers=self._auth_headers(),
        )
        assert resp.status_code in (200, 201, 400), resp.text
        return resp.json()

    def list_reviews(self, listing_id):
        resp = self.sess.get(f"{self.base_url}/reviews/", params={"listing": str(listing_id)})
        assert resp.status_code == 200, resp.text
        return resp.json()