from core.models import Application, Job
from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta

class AnalyticsEngine:

    @staticmethod
    def get_funnel(job_id):
        apps = Application.objects.filter(job_id=job_id)

        return {
            "applied": apps.filter(status="APPLIED").count(),
            "shortlisted": apps.filter(status="SHORTLISTED").count(),
            "interviewed": apps.filter(status="INTERVIEW_SCHEDULED").count(),
            "selected": apps.filter(status="SELECTED").count(),
        }

    @staticmethod
    def conversion_ratio(job_id):
        data = AnalyticsEngine.get_funnel(job_id)

        applied = data["applied"] or 1

        return {
            "shortlist_rate": round((data["shortlisted"] / applied) * 100, 2),
            "interview_rate": round((data["interviewed"] / applied) * 100, 2),
            "selection_rate": round((data["selected"] / applied) * 100, 2),
        }

    @staticmethod
    def job_performance():
        return Job.objects.annotate(
            total_applications=Count("application")
        ).values("title", "total_applications")
    
    @staticmethod
    def weekly_applications(job_id):
        last_7_days = now() - timedelta(days=7)

        return Application.objects.filter(
            job_id=job_id,
            applied_at__gte=last_7_days
        ).count()