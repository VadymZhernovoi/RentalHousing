import requests, random
from faker import Faker

import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RentalHousing.settings')
django.setup()

BASE_URL = "http://localhost:8000/api/v1"

def register_user():
    fake = Faker()
    email = fake.email()
    N = 10
    PWD = "YourStrongPass1!"
    fake = Faker("en_US")
    # fake.seed(PWD)

    for _ in range(N):
        base = fake.user_name()
        email = f"{base}{random.randint(1000,9999)}@example.com"
        payload = {
            "email": email,
            "username": f"{base}_{random.randint(1000,9999)}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "password": PWD,
            "password2": PWD,
            "role": random.choice(["renter", "lessor"]),
            "nickname": fake.first_name(),
        }
        r = requests.post(f"{BASE_URL}/user/register/", json=payload, timeout=10)
        print(r.status_code, email, r.text)

if __name__ == "__main__":
    create_users()
