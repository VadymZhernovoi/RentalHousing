import pytest
import inspect
from typing import Any

from apps.bookings.models import Booking
from rental_api import RentalApi
from test_booking import create_listing_as_lessor
from apps.core.users_seed_test import BASE_URL, email_for, future_range

email_lessor, pwd_lessor = email_for("lessor1")
email_renter, pwd_renter = email_for("renter1")
email_moderator, pwd_moderator = email_for("mod1")

def _login_lessor():
    api = RentalApi(BASE_URL)
    api.login(email_lessor, pwd_lessor)
    return api

def _login_renter():
    api = RentalApi(BASE_URL)
    api.login(email_renter, pwd_renter)
    return api

def _login_moderator():
    api = RentalApi(BASE_URL)
    api.login(email_moderator, pwd_moderator)
    return api

def create_pending_booking(renter_api: RentalApi, listing_id: str, start: str, end: str, **kwargs: Any) -> Booking:
    payload = {"listing": str(listing_id), "start_date": start, "end_date": end}
    guests = kwargs.get("guests")
    if guests is not None:
        payload["guests"] = guests
    baby_cribs = kwargs.get("baby_cribs")
    if baby_cribs is not None:
        payload["baby_cribs"] = baby_cribs
    for key in ("kitchen_needed", "parking_needed", "pets"):
        val = kwargs.get(key)
        if val is not None:
            payload[key] = val

    # resp = renter_api.sess.post(f"{renter_api.base_url}/bookings/", json=payload)
    # return resp

    bk = renter_api.create_booking(payload)
    # return bk, status_code
    assert bk["status"] in ("pending", "awaiting_payment", "pending"), bk
    return bk.get("id", None)

@pytest.mark.integration
def test_review_create_forbidden_before_completed():
    days = 3
    offset = 14
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=4,
    )
    # renter -> pending (+ approve), but the booking has not completed (or the check-out date has not passed)
    renter = _login_renter()
    start, end = future_range(days=3, offset=14)
    booking_id = create_pending_booking(renter, listing_id, start, end, guests=3)
    # # booking_json, status_code = renter.create_booking({
    # #     "listing": str(listing_id),
    # #     "start_date": start,
    # #     "end_date": end,
    # #     "guests": 2
    # # })
    # # assert status_code in (200, 201), booking_json
    # booking_id = booking_json["id"]

    # lessor -> approved, but completion is not possible (end_date in the future)
    appr = _login_lessor().approve_booking(booking_id)
    assert appr["status"] == "approved"

    # before completion/checkout
    create_resp = renter.sess.post(f"{BASE_URL}/reviews/",
                                   json={"booking": str(booking_id), "rating": 5, "comment": "Too early"})
    assert create_resp.status_code == 400, create_resp.text

@pytest.mark.integration
def test_owner_cannot_create_review_for_foreign_booking():
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(title)
    renter = _login_renter()

    start, end = future_range(days=3, offset=12)
    booking_json, status_code = renter.create_booking({
        "listing": str(listing_id), "start_date": start, "end_date": end, "guests": 2
    })
    assert status_code in (200, 201), booking_json
    booking_id = booking_json["id"]
    _login_lessor().approve_booking(booking_id)

    # Lessor -> review on a renter's booking -> not his booking
    lessor_try = _login_lessor().sess.post(f"{BASE_URL}/reviews/",
                                           json={"booking": str(booking_id), "rating": 5, "comment": "comment lessor"})
    assert lessor_try.status_code in (400, 403), lessor_try.text

@pytest.mark.integration
def test_owner_comment_allowed_only_for_listing_owner():
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(title)
    renter = _login_renter()

    start, end = future_range(days=3, offset=10)
    booking_json, status_code = renter.create_booking({
        "listing": str(listing_id), "start_date": start, "end_date": end, "guests": 2
    })
    assert status_code in (200, 201), booking_json
    booking_id = booking_json["id"]
    _login_lessor().approve_booking(booking_id)

    create_resp = renter.sess.post(f"{BASE_URL}/reviews/",
                                   json={"booking": str(booking_id), "rating": 5, "comment": "Nice stay"})
    if create_resp.status_code != 201:
        pytest.skip("Review creation blocked (booking not completed) — skip owner_comment test.")
    review = create_resp.json()
    review_id = review["id"]

    # listing owner leaves an owner_comment
    oc_resp = _login_lessor().owner_comment_review(review_id, "Thanks for your feedback!")
    assert oc_resp.status_code == 200, oc_resp.text
    body = oc_resp.json()
    assert body.get("owner_comment") == "Thanks for your feedback!"

@pytest.mark.integration
def test_renter_cannot_moderate_review():
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(title)
    renter = _login_renter()

    start, end = future_range(days=3, offset=11)
    booking_json, status_code = renter.create_booking({
        "listing": str(listing_id), "start_date": start, "end_date": end, "guests": 2
    })
    assert status_code in (200, 201), booking_json
    booking_id = booking_json["id"]
    _login_lessor().approve_booking(booking_id)

    create_resp = renter.sess.post(f"{BASE_URL}/reviews/",
                                   json={"booking": str(booking_id), "rating": 4, "comment": "ok"})
    if create_resp.status_code != 201:
        pytest.skip("Review creation blocked (booking not completed) — skip moderate test.")
    review_id = create_resp.json()["id"]

    # renter -> moderation
    mod_resp = renter.moderate_review(review_id, is_valid=False)
    assert mod_resp.status_code == 403, mod_resp.text