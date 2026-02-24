from django.db.models import Count
from .models import Job


class JobService:

    @staticmethod
    def get_queryset_for_user(user):
        queryset = (
            Job.objects
            .select_related("employer", "employer__user")
            .annotate(application_count=Count("application"))
        )

        if user.is_authenticated and user.role == "EMPLOYER":
            return queryset.filter(employer=user.employer_profile)

        return queryset.filter(status="OPEN")