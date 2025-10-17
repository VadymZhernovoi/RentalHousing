from django.db import models
from django.utils.translation import gettext_lazy as _

class Roles(models.TextChoices):
    RENTER = "renter", _("Renter")
    LESSOR = "lessor", _("Lessor")
    MODERATOR = "moderator", _("Moderator")
    ADMIN = "admin", _("Admin")

class Types(models.TextChoices):
    VILLA = "villa", _("Villa")
    HOUSE = "house", _("House")
    APARTMENT = "apartment", _("Apartment")
    PENTHOUSE = "penthouse", _("Penthouse")
    STUDIO = "studio", _("Studio")
    ROOM = "room", _("Room")
    OTHER = "other", _("Other")


class StatusBooking(models.TextChoices):
    PENDING = "pending", _("Pending")       # создано, ожидает решения владельца
    APPROVED = "approved", _("Approved")    # подтверждено владельцем, ждёт заезда
    DECLINED = "declined", _("Declined")    # отклонено владельцем
    CANCELLED = "cancelled", _("Cancelled") # отменено арендатором до дедлайна
    COMPLETED = "completed", _("Completed") # завершено


