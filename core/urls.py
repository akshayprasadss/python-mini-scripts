from django.urls import path
from .views import TestAPI, JobListCreateAPI

urlpatterns = [
    path('', TestAPI.as_view(), name='test-api'),
    path('jobs/', JobListCreateAPI.as_view(), name='jobs'),
]