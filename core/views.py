# ==============================
# Django & DRF Imports
# ==============================
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count
# ==============================
# JWT Imports
# ==============================
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
# ==============================
# Local Imports
# ==============================
from .models import (
    CustomUser,
    Job,
    Application,
    CandidateProfile,
    EmployerProfile,
)

from .serializers import (
    SignupSerializer,
    UserSerializer,
    JobSerializer,
    ApplicationSerializer,
    CandidateProfileSerializer,
    EmployerProfileSerializer,
)

from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
    NotFound,
)

from .permissions import IsEmployer, IsCandidate, IsAdmin
from .services import JobService

# =========================================================
# TEST API
# =========================================================
class TestAPI(APIView):
    def get(self, request):
        return Response({"message": "Test API working"}, status=200)


# =========================================================
# AUTH APIs
# =========================================================
class SignupAPI(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]


class LogoutAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logged out successfully"},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception:
            return Response(
                {"error": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST
            )


class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_verified:
            raise serializers.ValidationError("Account not verified")

        return data


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer


# =========================================================
# USER MANAGEMENT (Admin Only)
# =========================================================
class AdminUserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


# =========================================================
# JOB APIs
# =========================================================
class JobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsEmployer]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['status', 'created_at']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['created_at', 'salary']

    def get_queryset(self):
        return JobService.get_jobs_for_user(self.request.user)
    
class JobCreateView(generics.CreateAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, IsEmployer]

    def perform_create(self, serializer):
       try:
           employer_profile = self.request.user.employer_profile
       except EmployerProfile.DoesNotExist:
           raise PermissionDenied("You must create employer profile first.")

       serializer.save(employer=employer_profile)

class AdminDeleteJobView(generics.DestroyAPIView):
    queryset = Job.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]


# =========================================================
# JOB APPLICATION API
# =========================================================
class ApplyJobView(generics.CreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsCandidate]

    def perform_create(self, serializer):
        job_id = self.kwargs.get("pk")
        job = Job.objects.get(id=job_id)

        candidate_profile = self.request.user.candidate_profile

        # Prevent duplicate applications
        if Application.objects.filter(
            job=job,
            candidate=candidate_profile
        ).exists():
            raise PermissionDenied("You already applied to this job.")

        serializer.save(job=job, candidate=candidate_profile)


# =========================================================
# CANDIDATE PROFILE API (Day 11)
# =========================================================
class CandidateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    # CREATE PROFILE
    def post(self, request):

        if request.user.role != "CANDIDATE":
            raise PermissionDenied("Only candidates allowed")

        if hasattr(request.user, "candidate_profile"):
            raise ValidationError("Profile already exists")

        serializer = CandidateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # VIEW PROFILE
    def get(self, request):

        # Admin override
        if request.user.role == "ADMIN":
            profiles = CandidateProfile.objects.filter(is_active=True)
            serializer = CandidateProfileSerializer(profiles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.user.role != "CANDIDATE":
            raise PermissionDenied("Access denied")

        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound("Profile not found")

        serializer = CandidateProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # SOFT DELETE
    def delete(self, request):

        if request.user.role != "CANDIDATE":
            raise PermissionDenied("Access denied")

        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound("Profile not found")

        profile.is_active = False
        profile.save()

        return Response(
            {"message": "Profile deactivated successfully"},
            status=status.HTTP_200_OK
        )

    # UPDATE PROFILE
    def put(self, request):

        # Admin override
        if request.user.role == "ADMIN":

            profile_id = request.data.get("id")
            if not profile_id:
                raise ValidationError("Profile ID required")

            try:
                profile = CandidateProfile.objects.get(id=profile_id)
            except CandidateProfile.DoesNotExist:
                raise NotFound("Profile not found")

            serializer = CandidateProfileSerializer(
                profile,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)

        # Candidate update own profile
        if request.user.role != "CANDIDATE":
            raise PermissionDenied("Access denied")

        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound("Profile not found")

        serializer = CandidateProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

# =========================================================
# EMPLOYER PROFILE API (Day 11)
# =========================================================
class EmployerProfileView(APIView):
    permission_classes = [IsAuthenticated]

    # CREATE PROFILE
    def post(self, request):

        if request.user.role != "EMPLOYER":
            raise PermissionDenied("Only employers allowed")

        if hasattr(request.user, "employer_profile"):
            raise ValidationError("Profile already exists")

        serializer = EmployerProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # VIEW PROFILE
    def get(self, request):

        if request.user.role == "ADMIN":
            profiles = EmployerProfile.objects.filter(is_active=True)
            serializer = EmployerProfileSerializer(profiles, many=True)
            return Response(serializer.data)

        if request.user.role != "EMPLOYER":
            raise PermissionDenied("Access denied")

        try:
            profile = request.user.employer_profile
        except EmployerProfile.DoesNotExist:
            raise NotFound("Profile not found")

        serializer = EmployerProfileSerializer(profile)
        return Response(serializer.data)

    # UPDATE PROFILE
    def put(self, request):

        if request.user.role != "EMPLOYER":
            raise PermissionDenied("Access denied")

        try:
            profile = request.user.employer_profile
        except EmployerProfile.DoesNotExist:
            raise NotFound("Profile not found")

        serializer = EmployerProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    # SOFT DELETE
    def delete(self, request):

        if request.user.role != "EMPLOYER":
            raise PermissionDenied("Access denied")

        try:
            profile = request.user.employer_profile
        except EmployerProfile.DoesNotExist:
            raise NotFound("Profile not found")

        profile.is_active = False
        profile.save()

        return Response(
            {"message": "Profile deactivated successfully"},
            status=status.HTTP_200_OK
        )