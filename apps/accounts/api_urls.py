from django.urls import path
from rest_framework.routers import DefaultRouter
from .api_views import ClientViewSet, AccountViewSet, TransactionViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("accounts-list", AccountViewSet, basename="account")
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = router.urls
