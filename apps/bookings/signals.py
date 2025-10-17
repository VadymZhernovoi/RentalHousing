from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Booking, Listing

@receiver(pre_save, sender=Booking)
def booking_set_total_cost(sender, instance: Booking, **kwargs):
    """
    When creating and when changing dates/listing, we recalculate total_cost.
    """
    instance.total_cost = instance.calc_total_cost()
