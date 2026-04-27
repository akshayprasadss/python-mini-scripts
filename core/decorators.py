from rest_framework.exceptions import PermissionDenied
from core.services.subscription_service import has_active_subscription


def require_subscription(view_func):
    def wrapper(request, *args, **kwargs):
        if not has_active_subscription(request.user):
            raise PermissionDenied("Active subscription required")
        return view_func(request, *args, **kwargs)
    return wrapper