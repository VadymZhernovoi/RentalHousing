from django.db.models import F, Q
from django.db.models.aggregates import Count
from django.db.models.functions import Coalesce
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.decorators import action


from .filters import SearchQueryFilter
from ..core.roles import is_renter, is_moderator, is_admin, is_lessor
from ..statistics.models import SearchQueryStats, SearchQuery
from ..statistics.serializers import SearchQueryStatsSerializer, SearchQuerySerializer
from ..listings.serializers import ListingSerializer
from ..listings.models import Listing

@extend_schema(
    summary="List popular search keywords ordered by count (desc).",
    request=None,
    responses={200: OpenApiResponse(response=SearchQueryStatsSerializer,
                                    description="List of popular searches (paginated)")},
)
class PopularSearchesViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/statistics/popular/searches/ - list """
    serializer_class = SearchQueryStatsSerializer
    permission_classes = [permissions.AllowAny]
    queryset = SearchQueryStats.objects.order_by("-count", "-updated_at")

@extend_schema(
    description=(
        "List popular listings with aggregated counters.\n"
        "Annotated fields in response:\n"
        "- `views_cnt` (views), `reviews_cnt` (reviews), `rating_avg` (avg rating).\n"
        "Visibility rules:\n"
        "- anonymous / renter → only active\n"
        "- moderator / admin → all (active + inactive)\n"
        "- lessor → only own (default) OR `?all=true` → active + own inactive"
    ),
    request=None,
    responses={200: OpenApiResponse(response=ListingSerializer, description="List of popular listings (paginated)")},
)
class PopularListingsViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/statistics/popular/listings/ - list """
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = (
            Listing.objects.select_related("owner", "listing_stats")
            .annotate(
                views_cnt=Coalesce(F("listing_stats__views_count"), 0),
                reviews_cnt=Coalesce(F("listing_stats__reviews_count"), 0),
                rating_avg=Coalesce(F("listing_stats__avg_rating"), 0.0),
            )
            .order_by("-views_cnt", "-reviews_cnt", "-rating_avg")
        )
        user = self.request.user
        # anonymous/RENTER: active only
        if not user.is_authenticated or is_renter(user):
            return queryset.filter(is_active=True)
        # MODERATOR/ADMIN all (active + inactive)
        if is_moderator(user) or is_admin(user):
            return queryset
        # LESSOR
        if is_lessor(user):
            all_flag = self.request.query_params.get("all", "").lower() in {"1", "true", "yes"}
            if all_flag:
                # all active + your own inactive
                return queryset.filter(Q(is_active=True) | Q(owner_id=user.id, is_active=False))
            # default - only your own (active + inactive)
            return queryset.filter(owner_id=user.id)

        # default: only active
        return queryset.filter(is_active=True)

@extend_schema(
    description=(
        "List search history with filters.\n"
        "Query params:\n"
        "- `keyword` (substring in keywords)\n"
        "- `date_from`, `date_to`\n"
        "- `param` + `param_value` (filter by key/value stored in params)\n"
        "- `ordering` (e.g. -created_at)"
    ),
    request=None,
    responses={200: OpenApiResponse(response=SearchQuerySerializer,
                                    description="List of search queries (paginated)")},
)
class SearchQueryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/statistics/searches/?keyword=<substr>&date_from=&date_to=&param=&param_value=?ordering=-created_at
    GET /api/v1/statistics/searches/summary/?same_filters...  -  [{"keywords":"...", "count": N}, ...]
    """
    queryset = SearchQuery.objects.all().order_by("-created_at")
    serializer_class = SearchQuerySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = SearchQueryFilter
    search_fields = ["keywords"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    @extend_schema(
        description=(
                "Aggregated popular keywords subject to the same filters as list endpoint.\n"
                "Response: array of objects `{keywords, count}` ordered by `count desc`."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"keywords": {"type": "string"}, "count": {"type": "integer"},},
                    },
                },
                description="Aggregated popular keywords",
            )
        },
    )
    @action(detail=False, methods=["GET"], url_path="summary")
    def summary(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        data = (queryset.values("keywords").annotate(count=Count("id")).order_by("-count", "-keywords"))
        return Response(list(data))

