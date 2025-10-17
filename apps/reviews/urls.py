from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ReviewListCreateView

# router = DefaultRouter()
# router.register(r"reviews", ReviewViewSet, basename="review")
# urlpatterns = router.urls

urlpatterns = [
    path("reviews/", ReviewListCreateView.as_view(), name="review-list-create"),
    path("listings/<uuid:listing_id>/reviews/", ReviewListCreateView.as_view(), name="listing-review-list-create"),
]
