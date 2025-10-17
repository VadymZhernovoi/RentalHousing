from django.db import models
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    """
    Abstract model that provides created_at and updated_at timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        abstract = True