from rest_framework import viewsets, response, status
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from django.db.models.query_utils import Q
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, extend_schema_view

from ..core.permissions import BookingCreatePermission, BookingChangePermission, BookingApproveDeclineCompletePermission
from ..core.enums import StatusBooking
from .models import Booking
from .serializers import BookingCreateUpdateSerializer
from ..core.roles import is_admin, is_moderator, is_renter, is_lessor

@extend_schema_view(
    list=extend_schema(tags=["Bookings"], summary="List bookings"),
    retrieve=extend_schema(tags=["Bookings"], summary="Get booking"),
    create=extend_schema(tags=["Bookings"], summary="Create booking"),
    update=extend_schema(tags=["Bookings"], summary="Update booking"),
    partial_update=extend_schema(tags=["Bookings"], summary="Patch booking"),
    destroy=extend_schema(tags=["Bookings"], summary="Delete booking"),
)
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().select_related("listing", "renter")
    serializer_class = BookingCreateUpdateSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]  # add/change/view/delete booking

    def get_permissions(self):
        action = getattr(self, "action", None)
        if action == "create":
            return [IsAuthenticated(), BookingCreatePermission()]
        if action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), BookingChangePermission()]
        if action in ("approve", "decline", "completed"):
            return [IsAuthenticated(), BookingApproveDeclineCompletePermission()]
        return [perm() for perm in self.permission_classes]

    def get_queryset(self):
        """
        Filters reservations.
        Renter sees their reservations. Lessor sees reservations for their listings. Admin — all.
        :return: queryset
        """
        user = self.request.user
        qs = super().get_queryset().select_related("listing","renter")
        if is_admin(user) or is_moderator(user):
            return qs
        if is_renter(user):
            return qs.filter(renter=user)
        if is_lessor(user):
            return qs.filter(listing__owner=user)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(renter=self.request.user)

    @extend_schema(
        tags=["Bookings"],
        operation_id="booking_approve",
        summary="Approve booking",
        request=None,
        responses={
            200: OpenApiResponse(description="Booking approved"),
            400: OpenApiResponse(description="Only pending can be approved"),
            403: OpenApiResponse(description="Forbidden"),
            409: OpenApiResponse(description="Dates overlap with another approved booking"),
        },
        examples=[OpenApiExample("Success", value={"id": 123, "status": "approved"}, response_only=True)],
    )
    @action(detail=True, methods=["POST"])
    def approve(self, request, pk=None):
        """
        Action - Approve/Pending booking by Lessor
        :param request: POST /api/v1/bookings/{id}/approve/
        :return: retry with COMPLETED → 200
        """
        booking = self.get_object()
        user = request.user
        # Only the listing owner (lessor) or admin
        if not (is_admin(user) or (is_lessor(user) and booking.listing.owner_id == user.id)):
            return response.Response({"detail":"Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        # only PENDING
        if booking.status != StatusBooking.PENDING.value:
            return response.Response({"detail":"Only pending can be approved"}, status=status.HTTP_400_BAD_REQUEST)
        # if something was approved in parallel
        today = timezone.localdate()
        appr = getattr(StatusBooking.APPROVED,"value",StatusBooking.APPROVED)
        overlap = Booking.objects.filter(
            listing=booking.listing, status=StatusBooking.APPROVED.value, end_date__gt=today
            ).filter(Q(start_date__lt=booking.end_date) & Q(end_date__gt=booking.start_date)).exists()
        if overlap:
            return response.Response({"detail":"Dates overlap with another approved booking"}, status=status.HTTP_409_CONFLICT)
        # APPROVE
        booking.status = appr
        booking.save(update_fields=["status"])
        return response.Response({"id": booking.id, "status": booking.status}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Bookings"],
        operation_id="booking_decline",
        summary="Decline booking",
        request=None,
        responses={
            200: OpenApiResponse(description="Booking declined"),
            400: OpenApiResponse(description="Only pending can be declined"),
            403: OpenApiResponse(description="Forbidden"),
        },
    )
    @action(detail=True, methods=["POST"])
    def decline(self, request, pk=None):
        """
        Action - Decline booking by Lessor
        :param request: POST /api/v1/bookings/{id}/decline/
        :return: retry with COMPLETED → 200
        """
        booking = self.get_object()
        user = request.user
        # Only the listing owner (lessor) or admin
        if not (is_admin(user) or (is_lessor(user) and booking.listing.owner_id == user.id)):
            return response.Response({"detail":"Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != StatusBooking.PENDING.value:
            return response.Response({"detail":"Only pending can be declined"}, status=status.HTTP_400_BAD_REQUEST)
        # DECLINED
        booking.status = StatusBooking.DECLINED.value
        booking.save(update_fields=["status"])
        return response.Response({"id": booking.id, "status": booking.status}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Bookings"],
        operation_id="booking_cancel",
        summary="Cancel booking by renter before deadline",
        request={
            "application/json": {
                "type": "object",
                "properties": {"reason_cancel": {"type": "string"}},
            }
        },
        responses={
            200: OpenApiResponse(description="Cancelled"),
            400: OpenApiResponse(description="Deadline passed / wrong status"),
            403: OpenApiResponse(description="Forbidden"),
        },
        examples=[OpenApiExample("Success", value={"id": 123, "status": "cancelled"}, response_only=True)],
    )
    @action(detail=True, methods=["POST"])
    def cancelled(self, request, pk=None):
        """
        Action - Cancel booking by Renter (owner) before deadline
        :param request: POST /api/v1/bookings/{id}/cancelled/
        :return: retry on CANCELLED → 200
        """
        booking = self.get_object()
        user = request.user
        # only the booking owner (renter) or admin
        if not (is_admin(user) or (is_renter(user) and booking.renter_id == user.id)):
            return response.Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if str(booking.status) == str(StatusBooking.CANCELLED.value):
            return response.Response({"detail": "Already cancelled", "id": booking.id, "status": booking.status},
                                     status=status.HTTP_200_OK)
        # only PENDING/APPROVED
        allowed = {str(StatusBooking.PENDING.value), str(StatusBooking.APPROVED.value)}
        if str(booking.status) not in allowed:
            return response.Response({"detail": "Cannot cancel in current status"},
                                     status=status.HTTP_400_BAD_REQUEST)
        # cancellation deadline
        if not booking.is_can_be_cancellation():
            return response.Response(
                {"detail": "Cancel deadline passed", "cancel_deadline": booking.get_cancel_deadline().isoformat()},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # CANCELLED
        reason = request.data.get("reason_cancel", "")
        booking.status = StatusBooking.CANCELLED.value
        booking.reason_cancel = reason
        booking.save(update_fields=["status", "reason_cancel"])
    
        return response.Response({"id": booking.id, "status": booking.status}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Bookings"],
        operation_id="booking_complete",
        summary="Complete booking by lessor after checkout",
        request=None,
        responses={
            200: OpenApiResponse(description="Completed"),
            400: OpenApiResponse(description="Before checkout or wrong status"),
            403: OpenApiResponse(description="Forbidden"),
        },
        examples=[OpenApiExample("Success", value={"id": 123, "status": "completed"}, response_only=True)],
    )
    @action(detail=True, methods=["POST"])
    def completed(self, request, pk=None):
        """
        Action - Completed booking by Lessor (owner of the listing) after checkout
        :param request: POST /api/v1/bookings/{id}/completed/
        :return: retry on COMPLETED → 200
        """
        booking = self.get_object()
        user = request.user
        # Only the listing owner or admin
        if not (is_admin(user) or (is_lessor(user) and booking.listing.owner_id == user.id)):
            return response.Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        # not COMPLETED
        if str(booking.status) == str(StatusBooking.COMPLETED.value):
            return response.Response({"detail": "Already completed", "id": booking.id, "status": booking.status},
                status=status.HTTP_200_OK)
        # only APPROVED
        if str(booking.status) != str(StatusBooking.APPROVED.value):
            return response.Response({"detail": "Only approved bookings can be completed"},
                                     status=status.HTTP_400_BAD_REQUEST)
        # only after departure
        if booking.end_date > timezone.localdate():
            return response.Response(
                {"detail": "Cannot complete before checkout date", "end_date": str(booking.end_date)},
                status=status.HTTP_400_BAD_REQUEST)
        # COMPLETED
        booking.status = StatusBooking.COMPLETED.value
        booking.save(update_fields=["status"])
    
        return response.Response({"id": booking.id, "status": booking.status}, status=status.HTTP_200_OK)

# class BookingViewSet(viewsets.ModelViewSet):
#     queryset = Booking.objects.all().select_related("listing", "renter")
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_serializer_class(self):
#         if self.action in ["create"]:
#             return BookingCreateUpdateSerializer
#
#         return BookingListSerializer
#
#     def get_queryset(self):
#         """
#         Filters reservations.
#         Renter sees their reservations. Lessor sees reservations for their listings. Admin — all.
#         :return: queryset
#         """
#         user = self.request.user
#         queryset = super().get_queryset()
#
#         if user.role == Roles.RENTER:
#             return queryset.filter(renter=user)
#
#         if user.role == Roles.LESSOR:
#             return queryset.filter(listing__owner=user)
#
#         return queryset # Admin — all
#
#     def perform_create(self, serializer):
#         serializer.save(renter=self.request.user)
#
#
#     @action(detail=True, methods=["POST"], permission_classes=[IsLessor])
#     def approve(self, request, pk=None, *args, **kwargs):
#         """
#         Action - Approve/Pending booking by Lessor
#         :param request: POST /api/v1/bookings/{id}/approve/
#         :return: retry with COMPLETED → 200
#         """
#         booking = self.get_object()
#
#         if booking.listing.owner != request.user and request.user.role != "admin":
#             return response.Response(status=status.HTTP_403_FORBIDDEN)
#
#         if booking.status != StatusBooking.PENDING.value:
#             return response.Response({"detail": "Only pending can be approved"}, status=status.HTTP_400_BAD_REQUEST)
#         # check for date intersections if there has already been confirmation
#         today = timezone.localdate()
#         overlap = Booking.objects.filter(
#             listing=booking.listing,
#             status=StatusBooking.APPROVED,
#             start_date__lt=booking.end_date,
#             end_date__gt=booking.start_date,
#         ).filter(Q(end_date__gt=today)
#         ).exclude(pk=booking.pk).exists()
#         if overlap:
#             return response.Response(
#                 {"detail": "Dates overlap with an approved booking that has not finished yet"}, status=status.HTTP_409_CONFLICT
#             )
#
#         booking.status = StatusBooking.APPROVED.value
#         booking.save(update_fields=["status"])
#
#         return response.Response({"status": booking.status}, status=status.HTTP_200_OK)
#
#     @action(detail=True, methods=["POST"], permission_classes=[IsLessor])
#     def decline(self, request, pk=None, *args, **kwargs):
#         """
#         Action - Decline booking by Lessor
#         :param request: POST /api/v1/bookings/{id}/decline/
#         :return: retry with COMPLETED → 200
#         """
#         booking = self.get_object()
#
#         if booking.listing.owner != request.user and request.user.role != Roles.ADMIN:
#             return response.Response(status=status.HTTP_403_FORBIDDEN)
#
#         if booking.status != StatusBooking.PENDING.value:
#             return response.Response({"detail": "Only pending can be declined"}, status=status.HTTP_400_BAD_REQUEST)
#
#         booking.status = StatusBooking.DECLINED.value
#         booking.save(update_fields=["status"])
#
#         return response.Response({"status": booking.status}, status=status.HTTP_200_OK)
#
#
#     @action(detail=True, methods=["POST"], permission_classes=[permissions.IsAuthenticated, CanCancelBooking])
#     def cancel(self, request, pk=None, *args, **kwargs):
#         """
#         Action - Cancel booking by Renter or Admin
#         The deadline - from booking.get_cancel_deadline().
#         :param request: POST /api/v1/bookings/{id}/cancel/
#         :return: retry with COMPLETED → 200
#         """
#         booking = self.get_object()
#
#         if booking.status == StatusBooking.CANCELLED.value:
#             return response.Response({"detail": "Already cancelled"}, status=status.HTTP_200_OK)
#
#         serializer = BookingCancelSerializer(data=request.data, context={"request": request, "booking": booking})
#         serializer.is_valid(raise_exception=True)
#
#         booking.status = StatusBooking.CANCELLED.value
#         booking.reason_cancel = serializer.validated_data.get("reason_cancel", "")
#         booking.save(update_fields=["status", "reason_cancel"])
#
#         return response.Response(
#             {"id": booking.id, "status": booking.status, "cancel_deadline": booking.get_cancel_deadline().isoformat()},
#             status=status.HTTP_200_OK
#         )
#
#
#     @action(detail=True, methods=["POST"], permission_classes=[IsLessor])
#     def completed(self, request, pk=None, *args, **kwargs):
#         """
#         Completed booking by Lessor (owner of the listing).
#         POST /api/v1/bookings/{id}/completed/
#         Conditions:
#             - listing owner only (lessor/admin),
#             - status must be APPROVED,
#             - checkout date has already passed (end_date <= today),
#         :return: retry with COMPLETED → 200.
#         """
#
#         booking = self.get_object()
#
#         if booking.status == StatusBooking.COMPLETED.value:
#             return response.Response(
#                 {"detail": "Already completed", "id": booking.id, "status": booking.status},
#                 status=status.HTTP_200_OK,
#             )
#
#         # Only approved can be completed
#         if booking.status != StatusBooking.APPROVED.value:
#             return response.Response(
#                 {"detail": "Only approved bookings can be completed", "status": booking.status},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#
#         # cannot be completed before the departure date
#         today = timezone.localdate()
#         if booking.end_date > today:
#             return response.Response(
#                 {"detail": "Cannot complete before checkout date", "end_date": str(booking.end_date)},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#
#         # completed
#         booking.status = StatusBooking.COMPLETED
#         booking.save(update_fields=["status"])
#
#         return response.Response({"id": booking.id, "status": booking.status}, status=status.HTTP_200_OK)
