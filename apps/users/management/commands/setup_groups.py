from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from apps.core.permissions import ROLE_PERMS


def perm_qs(codes: list[str]):
    app_map = {}
    for full in codes:
        app_label, codename = full.split(".", 1)
        app_map.setdefault(app_label, []).append(codename)
    qs = Permission.objects.none()
    for app_label, codenames in app_map.items():
        qs |= Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames)
    return qs

class Command(BaseCommand):
    help = "Create groups (renter/lessor/moderator) and assign model permissions"

    def handle(self, *args, **kwargs):
        for role, codes in ROLE_PERMS.items():
            grp, _ = Group.objects.get_or_create(name=role)
            perms = perm_qs(codes)
            grp.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"{role}: {perms.count()} permissions assigned"))
        self.stdout.write(self.style.SUCCESS("Done"))
