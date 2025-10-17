from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bookings'
    verbose_name = 'Booking'
    verbose_name_plural = 'Bookings'

    def ready(self):
        from . import signals # noqa
