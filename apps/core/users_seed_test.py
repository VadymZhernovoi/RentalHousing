from datetime import date, timedelta

USERS = [
    # lessors
    {"email": "lessor1@example.com", "username": "lessor1", "first_name": "Lessor", "last_name": "One", "role": "lessor"},
    {"email": "lessor2@example.com", "username": "lessor2", "first_name": "Lessor", "last_name": "Two", "role": "lessor"},
    # renters
    {"email": "renter1@example.com", "username": "renter1", "first_name": "Renter", "last_name": "One", "role": "renter"},
    {"email": "renter2@example.com", "username": "renter2", "first_name": "Renter", "last_name": "Two", "role": "renter"},
    # moderators
    {"email": "moderator1@example.com", "username": "mod1", "first_name": "Mod", "last_name": "One", "role": "moderator"},
]

BASE_URL = "http://localhost:8000/api/v1"

DEFAULT_PASSWORD = "SecurePassword1!"

EMAIL_ADMIN = "admin@admin.com"
PWD_ADMIN = "Pa$$w0rd"

def email_for(username: str) -> str | None:
    for u in USERS:
        if u.get("username") == username:
            return u.get("email"), DEFAULT_PASSWORD
    return None

def future_range(days=3, offset=10):
    start = date.today() + timedelta(days=offset)
    end   = start + timedelta(days=days)
    return str(start), str(end)
