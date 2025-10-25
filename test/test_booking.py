import pytest
from datetime import date, timedelta

from rental_api import RentalApi, future_time, create_pending_booking, _login_renter, _login_lessor, create_listing_as_lessor
from apps.core.enums import Availability, StatusBooking
from apps.core.users_seed_test import BASE_URL, email_for

email_lessor2, pwd_lessor2 = email_for("lessor2")

# TESTS
@pytest.mark.integration
def test_create_and_approve_declines_overlapping_pending():
    start1, end1, days = future_time()
    #title = inspect.currentframe().f_code.co_name
    # lessor + listing
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+30,
        quests_max=4,
    )
    renter = _login_renter()

    # make two intersecting PENDING
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
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3
    )
    renter = _login_renter()

    # cancellation window is open (starts in offset days)
    booking_id = create_pending_booking(renter, listing_id, start, end)
    # renter cancels it
    renter = renter.cancel_booking(booking_id)  # POST /bookings/{id}/cancelled/
    assert renter.status_code in (200, 400), renter.text
    if renter.status_code == 200:
        assert renter.json()["status"] == StatusBooking.CANCELLED

@pytest.mark.integration
def test_not_owner_forbid_approve():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3
    )
    # renter makes pending
    renter = _login_renter()
    booking_id = create_pending_booking(renter, listing_id, start, end)
    # Not renter is trying to approve -> 403
    resp = renter.sess.post(f"{BASE_URL}/bookings/{booking_id}/approve/")
    assert resp.status_code == 403, resp.text

    # other lessor makes pending
    lessor2 = _login_lessor(email_lessor2)
    booking_id = create_pending_booking(renter, listing_id, start, end)
    # Not owner (other lessor) is trying to approve -> 403
    resp = lessor2.sess.post(f"{BASE_URL}/bookings/{booking_id}/approve/")
    assert resp.status_code == 404, resp.text

@pytest.mark.integration
def test_create_blocked_when_overlap_with_approved():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        ## title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3
    )
    renter = _login_renter()

    # first pending
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
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        ## title,
        span_days_min=days,
        span_days_max=days+10,
    )
    renter = _login_renter()
    booking_id = create_pending_booking(renter, listing_id, start, end)

    renter = lessor.decline_booking(booking_id)
    assert renter["status"] == StatusBooking.DECLINED

@pytest.mark.integration
def test_checking_excess_quests_max():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        ## title,
        span_days_min=days,
        span_days_max=days+10,
        quests_max=3,
    )
    # renter makes pending
    renter = _login_renter()
    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "guests": 4}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_checking_excess_baby_cribs_max():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+10,
        baby_cribs_max=3
    )
    # renter makes pending
    renter = _login_renter()
    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "baby_cribs": 4}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_checking_unavailability_kitchen():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+10,
        has_kitchen=Availability.NO
    )
    # renter makes pending
    renter = _login_renter()
    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "kitchen_needed": Availability.YES}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text

@pytest.mark.integration
def test_checking_unavailability_parken():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+10,
        parking_available=Availability.NO
    )
    # renter makes pending
    renter = _login_renter()
    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "parking_needed": Availability.YES}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text


@pytest.mark.integration
def test_checking_impossible_pets():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days+10,
        pets_possible=Availability.NO
    )
    # renter makes pending
    renter = _login_renter()
    payload = {"listing": str(listing_id), "start_date": start, "end_date": end, "pets": Availability.YES}
    resp = renter.sess.post(f"{BASE_URL}/bookings/", json=payload)
    assert resp.status_code in (400, 409), resp.text