from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    JobListView,
    JobCreateView,
    ApplyJobView,
    AdminDeleteJobView,
    AdminUserListView,
    SignupAPI,
    LogoutAPI,
    CustomTokenView,
    CandidateProfileView,
    EmployerProfileView
)

urlpatterns = [
    path("signup/", SignupAPI.as_view(), name="signup"),
    path('login/', CustomTokenView.as_view(), name='login'),
    path("token/", CustomTokenView.as_view(), name="token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutAPI.as_view(), name="logout"),
    path("users/", AdminUserListView.as_view(), name="users"),
    path('jobs/', JobListView.as_view(), name='jobs'),
    path('jobs/create/', JobCreateView.as_view(), name='job-create'),
    path("jobs/<int:pk>/apply/", ApplyJobView.as_view(), name="apply-job"),
    path("admin/jobs/<int:pk>/delete/", AdminDeleteJobView.as_view()), 
    path("profile/candidate/", CandidateProfileView.as_view()),
    path("profile/employer/", EmployerProfileView.as_view()),
]
