from django.utils import timezone
from core.models import UserSubscription
import logging

logger = logging.getLogger(__name__)


# ================= ROLE LOG =================
class RoleLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            logger.info(f"User: {request.user.email} | Role: {request.user.role}")

        return self.get_response(request)


# ================= REQUEST LOG =================
class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        return self.get_response(request)


# ================= SUBSCRIPTION CHECK =================
class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            sub = UserSubscription.objects.filter(
                user=request.user,
                is_active=True
            ).last()

            # auto-expire subscription
            if sub and sub.end_date < timezone.now():
                sub.is_active = False
                sub.save()
                logger.warning(f"Subscription expired for {request.user.email}")

        return self.get_response(request)