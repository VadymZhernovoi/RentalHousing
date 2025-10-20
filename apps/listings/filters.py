import django_filters as df
from .models import Listing

class ListingFilter(df.FilterSet):
    """
    Filters the list of Listing instances.
    """
    price_min = df.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = df.NumberFilter(field_name="price", lookup_expr="lte")
    rooms_min = df.NumberFilter(field_name="rooms", lookup_expr="gte")
    rooms_max = df.NumberFilter(field_name="rooms", lookup_expr="lte")
    guests = df.NumberFilter(field_name="max_guests", lookup_expr="gte")
    baby_cribs = df.NumberFilter(field_name="max_baby_crib", lookup_expr="gte")
    has_kitchen = df.BooleanFilter(field_name="filter_has_kitchen")
    parking_available = df.BooleanFilter(field_name="filter_parking_available")
    pets_possible = df.BooleanFilter(field_name="filter_pets_possible")

    city = df.CharFilter(field_name="city", lookup_expr="iexact")
    district = df.CharFilter(field_name="district", lookup_expr="iexact")
    type = df.CharFilter(field_name="type", lookup_expr="iexact")
    is_active = df.BooleanFilter(field_name="is_active")

    class Meta:
        model = Listing
        fields = []