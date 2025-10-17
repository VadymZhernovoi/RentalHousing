from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _

from ..core.enums import Roles


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, verbose_name=_("Role"))
    nickname = models.CharField(_("nickname"), max_length=30, blank=True, null=True, help_text=_("Visible to others"))

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    constraints = [models.CheckConstraint(check=Q(role__in=[r.value for r in Roles]), name="user_role_valid"),]

    def __str__(self):
        return f"{self.username} - {self.role}"