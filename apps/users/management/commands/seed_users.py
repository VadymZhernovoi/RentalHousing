from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.users_seed_test import USERS, DEFAULT_PASSWORD

User = get_user_model()

ROLES = ("lessor", "renter", "moderator")


class Command(BaseCommand):
    help = "Seed users with roles (lessor, renter, moderator)"

    def handle(self, *args, **options):
        for role in ROLES:
            Group.objects.get_or_create(name=role)

        created = 0
        for data in USERS:
            with transaction.atomic():
                user, was_created = User.objects.get_or_create(
                    email=data["email"],
                    defaults={
                        "username": data["username"],
                        "first_name": data.get("first_name", ""),
                        "last_name": data.get("last_name", ""),
                    },
                )
                # role
                if hasattr(user, "role"):
                    setattr(user, "role", data["role"])
                # group
                try:
                    group = Group.objects.get(name=data["role"])
                    user.groups.add(group)
                except Group.DoesNotExist:
                    pass

                if was_created:
                    user.set_password(DEFAULT_PASSWORD)
                    user.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"[OK] {data['email']} ({data['role']}) created"))
                else:
                    user.save(update_fields=["role"] if hasattr(user, "role") else [])
                    self.stdout.write(self.style.WARNING(f"[SKIP] {data['email']} already there"))

        self.stdout.write(self.style.SUCCESS(f"Done. Created Users: {created}/{len(USERS)}"))

