from rest_framework.routers import DefaultRouter

from .views import ProjectSubmissionViewSet

router = DefaultRouter()
router.register(r"", ProjectSubmissionViewSet, basename="submission")

urlpatterns = router.urls
