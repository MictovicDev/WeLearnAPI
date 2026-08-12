from rest_framework.routers import DefaultRouter
from .views import WalletViewSet

router = DefaultRouter()
router.register('wallet', WalletViewSet, basename='payments')