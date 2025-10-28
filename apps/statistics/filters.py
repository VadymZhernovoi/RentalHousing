import json

import django_filters as df
from django.db.models.query_utils import Q

from .models import SearchQuery

class SearchQueryFilter(df.FilterSet):
    keyword = df.CharFilter(field_name="keywords", lookup_expr="icontains")
    date_from = df.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = df.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    param = df.CharFilter(method="filter_param")

    class Meta:
        model = SearchQuery
        fields = []

    def _coerce_value(self, raw: str):
        """
        Casts a value from a string to the correct type for JSON comparison.
        """
        if raw is None:
            return None
        string = str(raw).strip()
        low = string.lower()
        # bool
        if low in ("true", "1", "yes", "y"):
            return True
        elif low in ("false","0","no","n"):
            return False

        # int/float
        try:
            return int(string)
        except ValueError:
            pass
        try:
            return float(string)
        except ValueError:
            pass
        # JSON literals (arrays/objects/numbers/booleans)
        try:
            return json.loads(string)
        except Exception:
            return string  # string

    def filter_param(self, queryset, name, param_key):
        """
        Filtering by key/value in the params JSON field.

        Requires both param and param_value to be specified.
        """
        param_value = self.data.get("param_value")
        if not param_key or param_value is None:
            return queryset

        value = self._coerce_value(param_value)

        try:
            return queryset.filter(**{"params__contains": {param_key: value}})

        except Exception:
            value_num = f'"{param_key}": {json.dumps(value)}'
            value_str = f'"{param_key}": "{value}"'
            return queryset.filter(Q(params__icontains=value_num) | Q(params__icontains=value_str))
