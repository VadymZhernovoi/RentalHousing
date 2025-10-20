import django_filters as df

from .models import SearchQuery

class SearchQueryFilter(df.FilterSet):
    keyword = df.CharFilter(field_name="keywords", lookup_expr="icontains")
    date_from = df.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = df.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    param = df.CharFilter(method="filter_param")

    class Meta:
        model = SearchQuery
        fields = []

    def filter_param(self, queryset, name, param_key):
        """
        Filtering by key/value in the params JSON field.
        Requires both param and param_value to be specified.
        """
        param_value = self.data.get("param_value")
        if not param_key or param_value is None:
            return queryset

        param_key_value = f'"{param_key}": ["{param_value}"]'

        return queryset.filter(params__icontains=param_key_value)
