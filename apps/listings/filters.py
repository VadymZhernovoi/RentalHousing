import django_filters as df

from .models import Listing
from ..core.enums import Availability

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

    has_kitchen = df.ChoiceFilter(field_name="has_kitchen", choices=Availability.choices)
    parking_available = df.ChoiceFilter(field_name="parking_available", choices=Availability.choices)
    pets_possible = df.ChoiceFilter(field_name="pets_possible", choices=Availability.choices)

    city = df.CharFilter(field_name="city", lookup_expr="iexact")
    district = df.CharFilter(field_name="district", lookup_expr="iexact")
    type_housing = df.CharFilter(field_name="type_housing", lookup_expr="iexact")
    is_active = df.BooleanFilter(field_name="is_active")

    class Meta:
        model = Listing
        fields = []

    def filter_choice(self, qs, name, value):
        val = str(value).lower()
        map_ = {"true": "y", "1": "y", "yes": "y",
                "false": "n", "0": "n", "no": "n",
                "unknown": "u", "none": "u", "null": "u"}
        c = map_.get(val)
        return qs if c is None else qs.filter(**{name: c})