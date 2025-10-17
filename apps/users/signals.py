from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.conf import settings
from django.apps import apps as dj_apps

User = dj_apps.get_model(settings.AUTH_USER_MODEL)

@receiver(post_save, sender=User)
def sync_role_group(sender, instance, created, **kwargs):
    if not created or instance.is_superuser or instance.is_staff:
        return
    try:
        group = Group.objects.get(name=instance.role)
        instance.groups.set([group])
    except Group.DoesNotExist:
        pass