from rest_framework.routers import DefaultRouter

from .api_views import AccountViewSet, ClientViewSet, TransactionViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("accounts-list", AccountViewSet, basename="account")
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = router.urls
