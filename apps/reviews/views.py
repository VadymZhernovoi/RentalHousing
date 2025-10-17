from rest_framework.decorators import action
from rest_framework import generics, mixins, viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets, permissions
from rest_framework.response import Response

from .models import Review
from .serializers import ReviewSerializer
from ..core.permissions import is_admin


class ReviewViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Review.objects.all().select_related("listing", "booking", "author")
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()
        listing_id = self.request.query_params.get("listing")
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["POST"])
    def moderate(self, request, pk=None):
        if not (request.user.has_perm("reviews.moderate_review") or is_admin(request.user)):
            return Response({"detail": "Forbidden"}, status=403)
        review = self.get_object()
        review.is_valid = bool(str(request.data.get("is_valid", "true")).lower() in {"1", "true", "yes"})
        review.save(update_fields=["is_valid"])
        return Response({"id": review.id, "is_valid": review.is_valid})

    @action(detail=True, methods=["POST"])
    def owner_comment(self, request, pk=None):
        review = self.get_object()
        user = request.user
        if (not (user.has_perm("reviews.owner_comment") and review.listing.owner_id == user.id) and
                not is_admin(user)):
            return Response({"detail": "Forbidden"}, status=403)
        review.owner_comment = request.data.get("owner_comment", "")
        review.save(update_fields=["owner_comment"])
        return Response({"id": review.id, "owner_comment": review.owner_comment})


class ReviewListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/reviews/?listing=<uuid>&my=true&ordering=-created_at
    POST /api/reviews/  { booking, rating, comment }   # Listing will be taken from Booking.
    GET/POST /api/listings/<uuid:listing_id>/reviews/  # Supports nested route
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["listing"]
    ordering_fields = ["created_at", "rating"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Review.objects.select_related("listing", "booking", "author")
        # nested route: /listings/<listing_id>/reviews/
        listing_id = self.kwargs.get("listing_id") or self.request.query_params.get("listing")
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)

        # ?my=true — only my reviews
        my = self.request.query_params.get("my", "").lower()
        if my in ["1", "true", "yes"]:
            if self.request.user.is_authenticated:
                queryset = queryset.filter(author=self.request.user)
            else:
                return Review.objects.none()
        return queryset

    def perform_create(self, serializer):
        """
        AUTHOR is taken from serializer.
        If a nested route is called, an additional check is made that booking belongs to the same listing.
        """
        listing_id = self.kwargs.get("listing_id")
        if listing_id:
            booking = serializer.validated_data["booking"]
            if str(booking.listing_id) != str(listing_id):
                raise ValidationError("Booking doesn't belong to this listing.")

        serializer.save()
