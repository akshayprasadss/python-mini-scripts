from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CreateOrderView,
    CreateSubscriptionPlanView,
    FailedPaymentsView,
    SubscriptionStatsView,
    TransactionsView,
    MonthlyRevenueView,
    RevenueView,
    JobAnalyticsView,
    candidate_report,
    AvailableSlotsView,
    BookInterviewView,
    InterviewScoreView,
    ReminderLogsView,
    SendReminderAPIView,
    AIInterviewFlowView,
    ATSMatchView,
    JobCandidateRankingView,
    JobListView,
    JobCreateView,
    ApplyJobView,
    AdminDeleteJobView,
    AdminUserListView,
    MyApplicationsView,
    SignupAPI,
    LogoutAPI,
    CustomTokenView,
    CandidateProfileView,
    EmployerProfileView,
    JobUpdateView,
    UpdateApplicationStatusView,
    EmployerJobListView,
    CandidateDashboardView,
    EmployerDashboardView,
    JobRecommendationView,
    ApplicationTimelineView,
    ApproveEmployerView,
    BlockUserView,
    AdminStatsView,
    AdminLogsView,
    ResumeParseView,
    RunAutoShortlistingView,
    SubscribeView,
)
schema_view = get_schema_view(
    openapi.Info(
        title="Zecpath API",
        default_version='v1',
        description="AI Hiring Backend APIs",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [

    # ================= AUTH =================
    path("signup/", SignupAPI.as_view()),
    path("login/", CustomTokenView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("logout/", LogoutAPI.as_view()),

    # ================= USERS =================
    path("users/", AdminUserListView.as_view()),

    # ================= JOBS =================
    path("jobs/", JobListView.as_view()),
    path("jobs/create/", JobCreateView.as_view()),
    path("jobs/<int:pk>/update/", JobUpdateView.as_view()),
    path("jobs/<int:pk>/delete/", AdminDeleteJobView.as_view()),
    path("jobs/<int:pk>/apply/", ApplyJobView.as_view()),

    # ================= APPLICATIONS =================
    path("applications/my/", MyApplicationsView.as_view()),
    path("applications/<int:pk>/status/", UpdateApplicationStatusView.as_view()),
    path("applications/<int:pk>/timeline/", ApplicationTimelineView.as_view()),

    # ================= PROFILES =================
    path("profile/candidate/", CandidateProfileView.as_view()),
    path("profile/employer/", EmployerProfileView.as_view()),

    # ================= DASHBOARD =================
    path("candidate/dashboard/", CandidateDashboardView.as_view()),
    path("candidate/recommendations/", JobRecommendationView.as_view()),
    path("employer/dashboard/", EmployerDashboardView.as_view()),
    path("employer/jobs/", EmployerJobListView.as_view()),

    # ================= ADMIN =================
    path("admin/employers/<int:pk>/approve/", ApproveEmployerView.as_view()),
    path("admin/users/<int:pk>/block/", BlockUserView.as_view()),
    path("admin/stats/", AdminStatsView.as_view()),
    path("admin/logs/", AdminLogsView.as_view()),

    # ================= AI / ATS =================
    path("resume/parse/", ResumeParseView.as_view()),
    path("jobs/<int:job_id>/match/", ATSMatchView.as_view()),
    path("jobs/<int:job_id>/candidates/ranking/", JobCandidateRankingView.as_view()),
    path("jobs/<int:job_id>/auto-process/", RunAutoShortlistingView.as_view()),

    # ================= AI INTERVIEW =================
    path("ai-interview/<int:job_id>/", AIInterviewFlowView.as_view()),
    path("ai-interview/<int:session_id>/score/", InterviewScoreView.as_view()),

    # ================= SCHEDULING =================
    path("jobs/<int:job_id>/slots/", AvailableSlotsView.as_view()),
    path("jobs/<int:job_id>/schedule/", BookInterviewView.as_view()),

    # ================= LOGS =================
    path("admin/reminder-logs/", ReminderLogsView.as_view()),
    path("send-reminders/", SendReminderAPIView.as_view()),

    # ================= REPORT =================
    path("candidate/<int:candidate_id>/report/", candidate_report),

    # ================= ANALYTICS =================
    path("jobs/<int:job_id>/analytics/", JobAnalyticsView.as_view()),

    # ================= SWAGGER =================
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),

    path("admin/revenue/", RevenueView.as_view()),
    path("admin/revenue/monthly/", MonthlyRevenueView.as_view()),
    path("admin/transactions/", TransactionsView.as_view()),
    path("admin/subscriptions/", SubscriptionStatsView.as_view()),
    path("admin/failed-payments/", FailedPaymentsView.as_view()),
    path("admin/create-plan/", CreateSubscriptionPlanView.as_view()),
    path("admin/create-order/", CreateOrderView.as_view()),
    path("subscribe/", SubscribeView.as_view()),
]