from core.models import UserSubscription
from django.utils import timezone


def has_active_subscription(user):
    sub = UserSubscription.objects.filter(
        user=user,
        is_active=True
    ).last()

    return sub and sub.end_date > timezone.now()


def has_feature(user, feature):
    sub = UserSubscription.objects.filter(
        user=user,
        is_active=True
    ).last()

    if not sub:
        return False

    plan = sub.plan

    features = {
        "AI_REPORT": plan.has_ai_access,
        "ANALYTICS": plan.has_analytics
    }

    return features.get(feature, False)