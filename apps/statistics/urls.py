from rest_framework.routers import DefaultRouter

from .views import PopularSearchesViewSet, PopularListingsViewSet, SearchQueryViewSet

router = DefaultRouter()
router.register(r"popular/searches", PopularSearchesViewSet, basename="popular-searches")
router.register(f"popular/listings", PopularListingsViewSet, basename="popular-listings")
router.register(r"searches", SearchQueryViewSet, basename="searches")
urlpatterns = router.urls