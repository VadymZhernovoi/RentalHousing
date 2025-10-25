from RentalHousing import settings

USERS = [
    # lessors
    {"email": "lessor1@example.com", "username": "lessor1", "first_name": "Lessor", "last_name": "One", "role": "lessor"},
    {"email": "lessor2@example.com", "username": "lessor2", "first_name": "Lessor", "last_name": "Two", "role": "lessor"},
    # renters
    {"email": "renter1@example.com", "username": "renter1", "first_name": "Renter", "last_name": "One", "role": "renter"},
    {"email": "renter2@example.com", "username": "renter2", "first_name": "Renter", "last_name": "Two", "role": "renter"},
    # moderators
    {"email": "moderator1@example.com", "username": "mod1", "first_name": "Mod", "last_name": "One", "role": "moderator"},
    # admin
    {"email": "admin@admin.com", "username": "admin", "first_name": "Admin", "last_name": "Adm", "role": "admin"},
]

BASE_URL = "http://" + settings.ALLOWED_HOSTS[-1] + ":8000/api/v1" # "http://localhost:8000/api/v1"

DEFAULT_PASSWORD = "SecurePassword1!"

EMAIL_ADMIN = "admin@admin.com"
PWD_ADMIN = "Pa$$w0rd"

def email_for(username: str) -> str | None:
    for u in USERS:
        if u.get("username") == username:
            return u.get("email"), DEFAULT_PASSWORD
    return None


