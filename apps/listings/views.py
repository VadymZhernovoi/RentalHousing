#from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework.decorators import action
from django.db.models.functions import Coalesce
from django.db.models import Q, F, Value, IntegerField, DecimalField
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse, OpenApiExample

from ..core.enums import StatusBooking
from ..bookings.models import Booking
from ..core.permissions import ListingCreatePermission, ListingChangeDeletePermission
from ..core.roles import is_renter, is_moderator, is_admin, is_lessor
from .models import Listing
from .serializers import ListingSerializer
from .filters import ListingFilter
from ..statistics.models import ListingView, ListingStats, SearchQuery, SearchQueryStats


def user_can_toggle(user):
    return user.has_perm("listings.toggle_active_listing") or is_admin(user)

@extend_schema(
    parameters=[
        OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="Full-text search in title/description"),
        OpenApiParameter("price_min", OpenApiTypes.DECIMAL, OpenApiParameter.QUERY),
        OpenApiParameter("price_max", OpenApiTypes.DECIMAL, OpenApiParameter.QUERY),
        OpenApiParameter("rooms_min", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("rooms_max", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("guests", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("baby_cribs", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("has_kitchen", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="Kitchen availability: y/n/u"),
        OpenApiParameter("parking_available", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="Parking availability: y/n/u"),
        OpenApiParameter("pets_possible", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="Pets possible: y/n/u"),
        OpenApiParameter("ordering", OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description="Sort fields. Ex: price,-created_at"),
        OpenApiParameter("all", OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                         description="For lessor: show active + own inactive"),
    ]
)
class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all().select_related("owner")
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny] # read for all

    filterset_class = ListingFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,]
    search_fields = ["title", "description"]
    ordering_fields = [
        "price",
        "created_at",
        "rooms",
        "popularity",
        "listing_stats__views_count",
        "listing_stats__reviews_count",
    ]
    ordering = ["-created_at"]

    def get_permissions(self):
        """
        Access rights depending on the action being performed (HTTP methods).
        """
        if self.action == "create": # for POST
            return [ListingCreatePermission()]

        if self.action in ("update", "partial_update", "destroy"): # for PUT/PATCH/DELETE
            return [ListingChangeDeletePermission()]

        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        """
        Saves the owner of the Listing instance.
        :param serializer:
        """
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        """
        Filters the list of Listing instances.

        - ?ordering=popularity (desc with -)
        - ?ordering=views or ?ordering=listing_stats__views_count (desc with -)
        - ?ordering=reviews or ?ordering=listing_stats__reviews_count (desc with -)
        Everyone sees only the ACTIVE status. The owner sees their own and INACTIVE statuses.
        """
        queryset = (super().get_queryset().select_related("owner", "listing_stats"))

        ordering_param = (self.request.query_params.get("ordering") or "").strip()
        # composite sorts
        if ordering_param in ("popularity", "-popularity"):
            desc = ordering_param.startswith("-")
            queryset = queryset.annotate(
                views_cnt=Coalesce(F("listing_stats__views_count"), Value(0), output_field=IntegerField()),
                reviews_cnt=Coalesce(F("listing_stats__reviews_count"), Value(0), output_field=IntegerField()),
                popularity=F("views_cnt") * 2 + F("reviews_cnt") * 4,
            )
            # visibility rules for a QuerySet
            queryset = self._apply_visibility(queryset)
            return queryset.order_by("-popularity" if desc else "popularity")

        # simple sorts
        if ordering_param:
            key = ordering_param.lstrip("-")
            desc = "-" if ordering_param.startswith("-") else ""
            if key in {"views", "listing_stats__views_count"}:
                queryset = queryset.order_by(f"{desc}listing_stats__views_count")
            elif key in {"reviews", "listing_stats__reviews_count"}:
                queryset = queryset.order_by(f"{desc}listing_stats__reviews_count")
            else:
                queryset = queryset.order_by(ordering_param)  # price , created_at, rooms ...

        # visibility rules for a QuerySet
        return self._apply_visibility(queryset)

    def _apply_visibility(self, queryset):
        """
        Sets visibility rules for a QuerySet.

        Everyone sees only the ACTIVE status. The owner sees their own and INACTIVE statuses.
        """
        user = self.request.user

        # anonymous/RENTER: active only
        if not user.is_authenticated or is_renter(user):
            return queryset.filter(is_active=True)

        # MODERATOR/ADMIN: все (active + inactive)
        if is_moderator(user) or is_admin(user):
            return queryset

        # LESSOR
        if is_lessor(user):
            all_flag = self.request.query_params.get("all", "").lower() in {"1", "true", "yes", "y"}
            if all_flag:
                # all active + your own inactive
                return queryset.filter(Q(is_active=True) | Q(owner_id=user.id, is_active=False))
            # default - only your own (active + inactive)
            return queryset.filter(owner_id=user.id)

        # default: only active
        return queryset.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        """
        Statistics: making a view counter increment.
        """
        instance = self.get_object()
        session_id = getattr(request, "session", None) and request.session.session_key or ""
        ListingView.objects.create(
            listing=instance,
            user=request.user if (request.user and request.user.is_authenticated) else None,
            session_id=session_id or "")
        stats, _ = ListingStats.objects.get_or_create(listing=instance)
        ListingStats.objects.filter(listing=instance).update(views_count=F("views_count") + 1)

        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        Statistics: saves search history.
        """
        queryset = request.query_params
        params = dict(queryset)
        # keywords
        keywords = queryset.get("search", "").strip()[:255]
        # remove unnecessary words from search parameters
        params.pop("page", None)
        params.pop("ordering", None)
        # cutting out keywords from parameters
        params.pop("search", None)
        if keywords or params:
            user = request.user if request.user.is_authenticated else None
            # save the session id
            session_id = ""
            session = getattr(request, "session", None)
            if session is not None:
                # create session_key
                session_id = session.session_key or ""
                if not session_id:
                    session.save()  # session.create()
                    session_id = session.session_key or ""
            # Search history
            SearchQuery.objects.create(user=user, session_id=session_id, keywords=keywords, params=params,)
            # Aggregated statistics by keywords
            if keywords:
                obj, created = SearchQueryStats.objects.get_or_create(keywords=keywords, defaults={"count": 1},)
                if not created:
                    SearchQueryStats.objects.filter(pk=obj.pk).update(count=F("count") + 1)

        return super().list(request, *args, **kwargs)

    def _find_blocking_booking(self, listing):
        """
        :param listing:
        :return: A reservation with the APPROVED status, for which the cancellation window has not yet closed,
        or None if edits are possible.
        """
        now = timezone.now()
        queryset = (Booking.objects
              .filter(listing=listing, status=StatusBooking.APPROVED.value)
              .only("id", "start_date", "end_date", "cancel_hours"))
        for booking in queryset:
            if now <= booking.get_cancel_deadline():
                return booking
        return None


    @extend_schema(
        summary="Listing update. The owner of your listing or admin.",
        responses={
            200: OpenApiResponse(description="Updated"),
            400: OpenApiResponse(description="Blocked by open cancel window of an approved booking"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    def perform_update(self, serializer):
        """
        Disable Listing editing after approval (or after the deadline).
        """
        listing = serializer.instance  # self.get_object()
        blocking = self._find_blocking_booking(listing)
        if blocking:
            raise ValidationError({
                "detail": "Listing cannot be edited while an approved booking still has an open cancel window.",
                "booking_id": blocking.id,
                "cancel_deadline": blocking.get_cancel_deadline().isoformat(),
            })
        serializer.save()


    @extend_schema(
        description="Toggle listing status (is_active).\n"
                    "The owner of your listing or a user with the permission "
                    "`listings.toggle_active_listing`/admin.\n"
                    "Can force the value via ?value=true|false.",
        request=None,
        responses={
            200: OpenApiResponse(description="Status updated / No change"),
            403: OpenApiResponse(description="Forbidden"),
        },
        examples=[
            OpenApiExample("Activated", value={"id": 70, "is_active": True}, response_only=True),
            OpenApiExample("Deactivated", value={"id": 70, "is_active": False}, response_only=True),
        ],
    )
    @action(detail=True, methods=["POST"], url_path="toggle-status", permission_classes=[permissions.IsAuthenticated])
    def toggle_status(self, request, pk=None, *args, **kwargs):
        """
        Toggle ACTIVE/INACTIVE status (is_active field).

        Permission: owner (lessor) for their own listing only, or user with the 'listings.toggle_active_listing' perm.
        """
        listing = self.get_object()
        user = request.user
        # permission: owner or listings.toggle_active_listing/admin
        if not ((is_lessor(user) and listing.owner_id == user.id) or user_can_toggle(user)):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        # optional: ?value=true|false
        value_param = request.query_params.get("value", "").lower()
        if value_param in {"true", "1", "yes", "y"}:
            new_value = True
        elif value_param in {"false", "0", "no", "n"}:
            new_value = False
        else:
            new_value = not listing.is_active
        # unnecessary update is exclude
        if listing.is_active == new_value:
            return Response(
                {"detail": "No change", "id": listing.id, "is_active": listing.is_active},
                status=status.HTTP_200_OK
            )

        listing.is_active = new_value
        listing.save(update_fields=["is_active"])
        return Response({"id": listing.id, "is_active": listing.is_active}, status=status.HTTP_200_OK)
