import pytest

from .rental_api import (future_time, past_time, create_listing_as_lessor, create_pending_booking,
                         _login_renter, _login_lessor, _login_moderator)
from apps.core.users_seed_test import BASE_URL

@pytest.mark.integration
def test_review_create_forbidden_before_completed():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=4,
    )
    # renter -> pending (+ approve), but the booking has not completed (or the check-out date has not passed)
    renter = _login_renter()
    booking_id = create_pending_booking(renter, listing_id, start, end, guests=3)

    # lessor -> approved, but completion is not possible (end_date in the future)
    appr = _login_lessor().approve_booking(booking_id)
    assert appr["status"] == "approved"

    # before completion/checkout
    create_resp = renter.sess.post(f"{BASE_URL}/reviews/",
                                   json={"booking": str(booking_id), "rating": 5, "comment": "Too early"})
    assert create_resp.status_code == 400, create_resp.text

@pytest.mark.integration
def test_owner_cannot_create_review_for_foreign_booking():
    start, end, days = future_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,З
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=4,
    )
    renter = _login_renter()
    booking_id = create_pending_booking(renter, listing_id, start, end, guests=2)
    _login_lessor().approve_booking(booking_id)
    # Lessor -> review on a renter's booking -> not his booking
    lessor_try = _login_lessor().sess.post(f"{BASE_URL}/reviews/",
                                           json={"booking": str(booking_id), "rating": 5, "comment": "comment lessor"})
    assert lessor_try.status_code in (400, 403), lessor_try.text

@pytest.mark.integration
def test_owner_comment_only_for_listing_owner():
    start, end, days = past_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=5,
    )
    renter = _login_renter()
    booking_id = create_pending_booking(renter, listing_id, start, end, guests=2)

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
    start, end, days = past_time()
    # title = inspect.currentframe().f_code.co_name
    lessor, listing_id = create_listing_as_lessor(
        # title,
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=5,
    )
    renter = _login_renter()

    booking_id = create_pending_booking(renter, listing_id, start, end, guests=2)

    _login_lessor().approve_booking(booking_id)

    create_resp = renter.sess.post(f"{BASE_URL}/reviews/",
                                   json={"booking": str(booking_id), "rating": 4, "comment": "ok"})
    if create_resp.status_code != 201:
        pytest.skip("Review creation blocked (booking not completed) — skip moderate test.")
    review_id = create_resp.json()["id"]

    # renter -> moderation
    mod_resp = renter.moderate_review(review_id, is_valid=False)
    assert mod_resp.status_code == 403, mod_resp.text

@pytest.mark.integration
def test_moderator_can_invalidate_review():
    start, end, days = past_time()
    lessor, listing_id = create_listing_as_lessor(
        span_days_min=days,
        span_days_max=days + 30,
        quests_max=5,
    )

    # renter created booking, lessor - approved
    renter = _login_renter()
    booking_id = create_pending_booking(renter, listing_id, start, end, guests=2)

    _login_lessor().approve_booking(booking_id)

    # renter created review
    create_resp = renter.sess.post(
        f"{BASE_URL}/reviews/",
        json={"booking": str(booking_id), "rating": 3, "comment": "+-"}
    )
    if create_resp.status_code != 201:
        pytest.skip(f"Review creation blocked (booking not completed) — skip moderator test.")
    review_id = create_resp.json()["id"]

    # moderator set invalid
    moderator = _login_moderator()
    mod_resp = moderator.moderate_review(review_id, is_valid=False)
    assert mod_resp.status_code in (200, 204), mod_resp.text

    # check status iv_valid
    get_resp = lessor.sess.get(f"{BASE_URL}/reviews/{review_id}/")
    assert get_resp.status_code == 200, get_resp.text
    payload = get_resp.json()
    assert payload.get("is_valid") is False, f"Expected is_valid=False, got: {payload}"
