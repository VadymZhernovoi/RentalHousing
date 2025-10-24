from typing import Any
import inspect

import pytest
from datetime import date, timedelta

from rental_api import RentalApi
from apps.bookings.models import Booking
from apps.core.enums import Availability, StatusBooking
from apps.core.users_seed_test import BASE_URL, email_for, future_range


email_lessor, pwd_lessor = email_for("lessor1")
email_lessor2, pwd_lessor2 = email_for("lessor2")
email_renter, pwd_renter = email_for("renter1")



def create_listing_as_lessor(title="API Test Listing", *args, **kwargs) -> RentalApi:
    lessor = RentalApi(BASE_URL)
    lessor.login(email_lessor, pwd_lessor)
    user_l = lessor.user()
    code, body = lessor.create_listing(user_l, title, True, **kwargs)
    assert code in (200, 201), body
    return lessor, body["id"]

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


# TESTS
@pytest.mark.integration
def test_create_and_approve_declines_overlapping_pending():
    days = 3
    offset = 14
    title = inspect.currentframe().f_code.co_name
    # lessor + listing
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+30,
        quests_max=4,
    )
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)

    # make two intersecting PENDING
    start1, end1 = future_range(days=days, offset=offset)
    start2, end2 = (date.fromisoformat(start1) + timedelta(days=1), date.fromisoformat(end1) + timedelta(days=1))
    start2, end2 = str(start2), str(end2)
    booking1_id = create_pending_booking(renter, listing_id, start1, end1, guests=3)
    booking2_id = create_pending_booking(renter, listing_id, start2, end2, guests=2)

    # lessor approves the first
    appr = lessor.approve_booking(booking1_id)
    assert appr["status"] == StatusBooking.APPROVED
    # the second one should become a DECLINED signal
    booking2 = renter.get_booking(booking2_id)
    assert booking2.status_code == 200, booking2.text
    assert booking2.json()["status"] == StatusBooking.DECLINED

@pytest.mark.integration
def test_cancelled_by_renter_before_deadline():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3
    )
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)

    # cancellation window is open (starts in offset days)
    start, end = future_range(days=days, offset=offset)
    booking_id = create_pending_booking(renter, listing_id, start, end)
    # renter cancels it
    renter = renter.cancel_booking(booking_id)  # POST /bookings/{id}/cancelled/
    assert renter.status_code in (200, 400), renter.text
    if renter.status_code == 200:
        assert renter.json()["status"] == StatusBooking.CANCELLED

@pytest.mark.integration
def test_not_owner_forbid_approve():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3
    )
    # renter makes pending
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)
    booking_id = create_pending_booking(renter, listing_id, start, end)
    # Not renter is trying to approve -> 403
    resp = renter.sess.post(f"{BASE_URL}/bookings/{booking_id}/approve/")
    assert resp.status_code == 403, resp.text

    # other lessor makes pending
    lessor2 = RentalApi(BASE_URL)
    lessor2.login(email_lessor2, pwd_lessor2)
    start, end = future_range(days=days, offset=offset)
    booking_id = create_pending_booking(renter, listing_id, start, end)
    # Not owner (other lessor) is trying to approve -> 403
    resp = renter.sess.post(f"{BASE_URL}/bookings/{booking_id}/approve/")
    assert resp.status_code == 403, resp.text

@pytest.mark.integration
def test_create_blocked_when_overlap_with_approved():
    days = 3
    offset = 10
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3
    )
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)

    # first pending
    start, end = future_range(days=days, offset=offset)
    booking1_id = create_pending_booking(renter, listing_id, start, end)
    # approve it
    appr = lessor.approve_booking(booking1_id)
    assert appr["status"] == StatusBooking.APPROVED
    # attempt to create another intersecting one → expect 400/409
    start2, end2 = (date.fromisoformat(start) + timedelta(days=1), date.fromisoformat(end) + timedelta(days=1))
    start2, end2 = str(start2), str(end2)
    payload = {"listing": str(listing_id), "start_date": start2, "end_date": end2, "guests": 2}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_decline_pending_by_lessor():
    days = 3
    offset = 10
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
    )
    renter = RentalApi(BASE_URL); renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)
    booking_id = create_pending_booking(renter, listing_id, start, end)

    renter = lessor.decline_booking(booking_id)
    assert renter["status"] == StatusBooking.DECLINED

@pytest.mark.integration
def test_checking_excess_quests_max():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        guests_max=3
    )
    # renter makes pending
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)

    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "guests": 4}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_checking_excess_baby_cribs_max():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        baby_cribs_max=3
    )
    # renter makes pending
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)

    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "baby_cribs": 4}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_checking_unavailability_kitchen():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        has_kitchen=Availability.NO
    )
    # renter makes pending
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)

    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "kitchen_needed": Availability.YES}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_checking_unavailability_parken():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        parking_available=Availability.NO
    )
    # renter makes pending
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)

    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "parking_needed": Availability.YES}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text


@pytest.mark.integration
def test_checking_impossible_pets():
    days = 4
    offset = 20
    title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        title,
        span_days_min=days,
        span_days_max=days+10,
        pets_possible=Availability.NO
    )
    # renter makes pending
    renter = RentalApi(BASE_URL)
    renter.login(email_renter, pwd_renter)
    start, end = future_range(days=days, offset=offset)

    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "pets": Availability.YES}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text