# ==============================
# Django & DRF Imports
# ==============================
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from .models import ReminderLog
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta
# ==============================
# JWT Imports
# ==============================
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# ==============================
# CORE LOGIC IMPORTS
# ==============================
from core.services.analytics_engine import AnalyticsEngine
from core.services.eligibility import check_ai_call_eligibility
from core.tasks import process_ai_call, parse_resume_task, send_email_task
from core.models import AIQuestionTemplate
import pdfplumber
import re

# ==============================
# Local Imports
# ==============================
from .models import (
    AIAnswer,
    CustomUser,
    Job,
    Application,
    CandidateProfile,
    EmployerProfile,
    ApplicationStatusLog,
    AdminActionLog,
    AIInterviewSession,

)

from .serializers import (
    SignupSerializer,
    UserSerializer,
    JobSerializer,
    ApplicationSerializer,
    CandidateProfileSerializer,
    EmployerProfileSerializer,
)

from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound


from .permissions import IsEmployer, IsCandidate, IsAdmin
from .services import JobService, calculate_match_score, auto_process_application
from core.services.ai_flow_manager import AIFlowManager

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.services.question_engine import QuestionEngine
from rest_framework.decorators import api_view,permission_classes
from core.services.ai_engine import AIEngine
from core.services.scoring_engine import ScoringEngine
from core.services.scheduling_engine import SchedulingEngine
from core.models import AvailabilitySlot, InterviewSchedule, SubscriptionPlan, PaymentTransaction, UserSubscription
from core.tasks import run_reminder_engine
from core.services.payment_service import create_order, verify_payment
from .services.report_engine import *
from core.decorators import require_subscription
from core.services.subscription_service import has_feature
from core.throttles import PremiumThrottle

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



# JOB APIs

class JobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['status', 'created_at', 'job_type']
    search_fields = ['title', 'description', 'location', 'skills']
    ordering_fields = ['created_at', 'salary_min', 'salary_max']

    def get_queryset(self):
        queryset = Job.objects.filter(
            is_active=True,
            status=Job.Status.OPEN
        )

        min_salary = self.request.query_params.get("min_salary")
        max_salary = self.request.query_params.get("max_salary")

        if min_salary:
            queryset = queryset.filter(salary_min__gte=min_salary)

        if max_salary:
            queryset = queryset.filter(salary_max__lte=max_salary)

        return queryset

class JobUpdateView(generics.UpdateAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin can update any job
        if user.role == user.Role.ADMIN:
            return Job.objects.all()

        # Employer can update only their jobs
        if user.role == user.Role.EMPLOYER:
            return Job.objects.filter(employer__user=user)

        return Job.objects.none()
    
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
        job = get_object_or_404(Job, id=self.kwargs["pk"])

        try:
            candidate_profile = self.request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise ValidationError("Candidate profile not found")

        # prevent duplicate
        if Application.objects.filter(
            job=job,
            candidate=candidate_profile
        ).exists():
            raise PermissionDenied("Already applied")

        # ✅ create first
        application = serializer.save(
            job=job,
            candidate=candidate_profile
        )

        # ✅ then process
        auto_process_application(application)

        return application
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

class MyApplicationsView(generics.ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role != user.Role.CANDIDATE:
            return Application.objects.none()

        # Safe profile lookup
        try:
            candidate_profile = user.candidate_profile
        except CandidateProfile.DoesNotExist:
            return Application.objects.none()

        return Application.objects.filter(
            candidate=candidate_profile
        ).select_related("job", "candidate__user").order_by("-applied_at")
    
class UpdateApplicationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):

        try:
            application = Application.objects.get(pk=pk)
        except Application.DoesNotExist:
            return Response(
                {"error": "Application not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 🔐 Ensure employer owns the job
        if application.job.employer.user != request.user:
            return Response(
                {"error": "Not authorized"},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get("status")

        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🚦 Workflow validation
        if not application.can_transition(new_status):
            return Response(
                {"error": "Invalid status transition"},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = application.status

        application.status = new_status
        application.save()

        send_email_task.delay(
            subject="Application Status Updated",
            message=f"Your application status changed to {new_status}",
            recipient_email=application.candidate.user.email
        )

        # create timeline log
        ApplicationStatusLog.objects.create(
            application=application,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user
        )
        return Response(
            {"message": "Status updated successfully"}
        )
    
class EmployerJobListView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Job.objects.filter(
            employer__user=self.request.user
        ).order_by("-id")
    
class ApplicationTimelineView(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request, pk):

        try:
            application = Application.objects.get(pk=pk)
        except Application.DoesNotExist:
            raise NotFound("Application not found")

        # Ensure candidate owns this application
        if application.candidate.user != request.user:
            raise PermissionDenied("Access denied")

        logs = ApplicationStatusLog.objects.filter(
            application=application
        ).order_by("changed_at")

        data = [
            {
                "old_status": log.old_status,
                "new_status": log.new_status,
                "changed_at": log.changed_at
            }
            for log in logs
        ]

        return Response(data)

class JobRecommendationView(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request):

        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound("Candidate profile not found")

        skills = profile.skills

        if not skills:
            jobs = Job.objects.filter(status=Job.Status.OPEN)[:10]
        else:
            skill_list = [skill.strip() for skill in skills.split(",")]

            jobs = Job.objects.filter(
                status=Job.Status.OPEN
            )

            # basic matching
            for skill in skill_list:
                jobs = jobs.filter(skills__icontains=skill)

        serializer = JobSerializer(jobs, many=True)

        return Response(serializer.data)

class CandidateDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request):

        try:
            profile = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            raise NotFound("Candidate profile not found")

        applications = Application.objects.filter(candidate=profile)

        data = {
            "total_applications": applications.count(),
            "shortlisted": applications.filter(status="SHORTLISTED").count(),
            "interviews": applications.filter(status="INTERVIEW_SCHEDULED").count(),
            "selected": applications.filter(status="SELECTED").count(),
            "rejected": applications.filter(status="REJECTED").count(),
        }

        return Response(data)

class EmployerDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsEmployer]

    def get(self, request):

        try:
            employer = request.user.employer_profile
        except EmployerProfile.DoesNotExist:
            raise NotFound("Employer profile not found")

        jobs = Job.objects.filter(employer=employer)
        applications = Application.objects.filter(
            job__employer=employer
        ).select_related("job", "candidate__user")

        data = {
            "total_jobs": jobs.count(),
            "open_jobs": jobs.filter(status="OPEN").count(),
            "closed_jobs": jobs.filter(status="CLOSED").count(),

            "total_applications": applications.count(),

            "shortlisted": applications.filter(status="SHORTLISTED").count(),
            "interviews": applications.filter(status="INTERVIEW_SCHEDULED").count(),
            "selected": applications.filter(status="SELECTED").count(),
            "rejected": applications.filter(status="REJECTED").count(),
        }

        return Response(data)

class ApproveEmployerView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        employer = get_object_or_404(EmployerProfile, pk=pk)

        employer.verification_status = True
        employer.save()

        AdminActionLog.objects.create(
            admin=request.user,
            action=f"Approved employer {employer.user.email}"
        )

        return Response({"message": "Employer approved successfully"})
    
class BlockUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        user = CustomUser.objects.get(pk=pk)

        user.is_active = False
        user.save()

        AdminActionLog.objects.create(
            admin=request.user,
            action=f"Blocked user {user.email}"
        )

        return Response({"message": "User blocked"})

class AdminLogsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        logs = AdminActionLog.objects.all().order_by("-created_at")

        data = [
            {
                "admin": log.admin.email,
                "action": log.action,
                "time": log.created_at
            }
            for log in logs
        ]

        return Response(data)
    
    
class AdminStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):

        data = {
            "total_users": CustomUser.objects.count(),
            "total_candidates": CustomUser.objects.filter(role="CANDIDATE").count(),
            "total_employers": CustomUser.objects.filter(role="EMPLOYER").count(),
            "total_jobs": Job.objects.count(),
            "total_applications": Application.objects.count(),
        }

        return Response(data)
    
class ResumeParseView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        resume = request.FILES.get("resume")

        if not resume:
            return Response({"error": "Resume file required"}, status=400)

        text = ""

        with pdfplumber.open(resume) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        cleaned_text = re.sub(r'\s+', ' ', text).strip()
        tokens = cleaned_text.lower().split()

        # skill detection
        skills_db = ["python","django","mysql","html","css","javascript","react","aws"]

        found_skills = [
            skill for skill in skills_db
            if skill in tokens
        ]

        # STEP 1 — convert list → string
        skills_string = ",".join(found_skills)
        
        # experience detection
        exp_match = re.search(r'(\d+)\s+years?', cleaned_text.lower())
        experience_years = exp_match.group(1) if exp_match else None

        # role detection
        roles_db = [
                "developer",
                "software engineer",
                "backend developer",
                "frontend developer",
                "data scientist"
        ]

        detected_role = None

        for role in roles_db:
           if role in cleaned_text.lower():
             detected_role = role
             break

        # email extraction
        email_match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', cleaned_text)
        email = email_match.group(0) if email_match else None

        # phone extraction
        phone_match = re.search(r'(\+?\d[\d\s\-]{8,15})', cleaned_text)
        phone = phone_match.group(0).strip() if phone_match else None
        exp_match = re.search(r'(\d+)\s+years?', cleaned_text.lower())
        experience_years = exp_match.group(1) if exp_match else None

        # name
        name = " ".join(cleaned_text.split(" ")[0:2])

        return Response({
                "name": name,
                "email": email,
                "phone": phone,
                "skills": found_skills,
                "experience_years": experience_years,
                "role": detected_role,
                "tokens": tokens[:20],
                "cleaned_text": cleaned_text
        })
    
class ATSMatchView(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]

    def post(self, request, job_id):

        # get job
        job = Job.objects.get(id=job_id)

        # get candidate profile
        profile = request.user.candidate_profile

        # get candidate skills
        candidate_skills = profile.skills.split(",") if profile.skills else []

        # calculate score
        score, matched, missing = calculate_match_score(candidate_skills, job.skills, profile.experience, job.experience)

        return Response({
            "job_title": job.title,
            "match_score": score,
            "matched_skills": matched,
            "missing_skills": missing
        })

class JobCandidateRankingView(APIView):
    permission_classes = [IsAuthenticated, IsEmployer]

    def get(self, request, job_id):

        job = Job.objects.get(id=job_id)

        applications = Application.objects.filter(
            job=job
        ).select_related("candidate__user")

        results = []

        for app in applications:
            candidate = app.candidate

            skills = candidate.skills.split(",") if candidate.skills else []

            score, _, _ = calculate_match_score(
                skills,
                job.skills,
                candidate.experience,
                job.experience
            )

            results.append({
                "candidate": candidate.user.email,
                "score": score
            })

        # sort highest score first
        results.sort(key=lambda x: x["score"], reverse=True)

        return Response(results)

class RunAutoShortlistingView(APIView):
    permission_classes = [IsAuthenticated, IsEmployer]

    def post(self, request, job_id):

        job = get_object_or_404(Job, id=job_id)

        # ensure employer owns job
        if job.employer.user != request.user:
            raise PermissionDenied("Not allowed")

        applications = Application.objects.filter(job=job)

        count = 0

        for app in applications:
            auto_process_application(app)
            count += 1

        return Response({
            "message": f"{count} applications processed"
        })

class AIInterviewFlowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):

        job = get_object_or_404(Job, id=job_id)

        session, created = AIInterviewSession.objects.get_or_create(
            user=request.user,
            job=job,
            is_completed=False
        )

        flow = AIFlowManager(session)

        answer = request.data.get("answer")
        question_id = request.data.get("question_id")

        # ✅ SAVE ANSWER THROUGH FLOW
        if answer and question_id:
            try:
                question = AIQuestionTemplate.objects.get(id=question_id)

                # ✅ Save answer
                flow.save_answer(question, answer)

                # ✅ Get latest answer safely
                ai_answer = AIAnswer.objects.filter(
                    session=session,
                    question=question
                ).last()

                # ❌ If not found → prevent crash
                if not ai_answer:
                    return Response(
                        {"error": "Answer not saved properly"},
                        status=500
                    )

                # ✅ Scoring
                scores = ScoringEngine.evaluate(answer, question)

                ai_answer.keyword_score = scores.get("keyword_score", 0)
                ai_answer.relevance_score = scores.get("relevance_score", 0)
                ai_answer.completeness_score = scores.get("completeness_score", 0)
                ai_answer.final_score = scores.get("final_score", 0)
                ai_answer.ai_feedback = scores.get("feedback", "")

                ai_answer.save()

            except AIQuestionTemplate.DoesNotExist:
                return Response({"error": "Invalid question_id"}, status=400)

            except Exception as e:
                return Response(
                    {"error": f"Something went wrong: {str(e)}"},
                    status=500
                )

        # ✅ GET NEXT QUESTION FROM FLOW (IMPORTANT)
        next_question = flow.get_next_question()

        if not next_question:
            session.is_completed = True
            session.save()
            return Response({"message": "Interview completed"})

        return Response({
            "session_id": session.id,
            "question_id": next_question.id,
            "question": next_question.text,
            "category": next_question.category
        })
    

class InterviewScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):

        answers = AIAnswer.objects.filter(session_id=session_id)

        total_score = sum(a.final_score or 0 for a in answers)
        count = answers.count()

        avg_score = total_score / count if count else 0

        data = [
            {
                "question": a.question.text,
                "answer": a.answer,
                "score": a.final_score,
                "feedback": a.ai_feedback
            }
            for a in answers
        ]

        return Response({
            "average_score": round(avg_score, 2),
            "answers": data
        })
    
class BookInterviewView(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]

    def post(self, request, job_id):

        try:
            candidate = request.user.candidate_profile
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Candidate profile not found"}, status=400)

        slot_id = request.data.get("slot_id")

        if not slot_id:
            return Response({"error": "slot_id required"}, status=400)

        job = get_object_or_404(Job, id=job_id)

        try:
            schedule = SchedulingEngine.book_slot(candidate, job, slot_id)

            # ✅ EMAIL TRIGGER
            send_email_task.delay(
                subject="Interview Scheduled",
                message=f"Your interview is scheduled at {schedule.scheduled_at}",
                email=candidate.user.email
            )

            return Response({
                "message": "Interview scheduled successfully",
                "scheduled_at": schedule.scheduled_at
            })

        except Exception as e:
            return Response({"error": str(e)}, status=400)
        
class AvailableSlotsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):

        slots = AvailabilitySlot.objects.filter(
            is_booked=False,
            date__gte=timezone.now().date()
        ).order_by("date", "start_time")

        data = [
            {
                "slot_id": s.id,
                "date": s.date,
                "start_time": s.start_time,
                "end_time": s.end_time
            }
            for s in slots
        ]

        return Response(data)
    
class ReminderLogsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):

        logs = ReminderLog.objects.all().order_by("-sent_at")

        data = [
            {
                "candidate": log.schedule.candidate.user.email,
                "job": log.schedule.job.title,
                "type": log.reminder_type,
                "status": log.status,
                "time": log.sent_at
            }
            for log in logs
        ]

        return Response(data)

class SendReminderAPIView(APIView):

    def post(self, request):
        run_reminder_engine.delay()
        return Response({"message": "Reminder process started"})
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@require_subscription
def candidate_report(request, candidate_id):

    # 🔐 ROLE CHECK
    if request.user.role not in ["ADMIN", "EMPLOYER"]:
        return Response(
            {"error": "Access denied"},
            status=status.HTTP_403_FORBIDDEN
        )

    # 🎯 GET PROFILE
    try:
        profile = CandidateProfile.objects.get(id=candidate_id)
    except CandidateProfile.DoesNotExist:
        return Response(
            {"error": "Candidate not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 🔒 EMPLOYER ACCESS CONTROL (IMPORTANT)
    if request.user.role == "EMPLOYER":
        has_access = Application.objects.filter(
            candidate=profile
        ).filter(
            job__employer__user=request.user
        ).exists()

        if not has_access:
            return Response(
                {"error": "You are not allowed to view this candidate"},
                status=status.HTTP_403_FORBIDDEN
            )

    # 📊 SCORES
    ats_score = get_ats_score(profile)
    ai_score = get_ai_score(profile)
    overall = calculate_overall(ats_score, ai_score)

    # 🧠 REPORT DATA
    report = {
        "candidate_email": profile.user.email,
        "experience": profile.experience,
        "skills": profile.skills,

        "ats_score": ats_score,
        "ai_call_score": ai_score,
        "overall_score": overall,

        "strengths": generate_strengths(profile),
        "risks": generate_risks(profile),
        "summary": generate_summary(profile.user.email, overall),
        "recommendation": get_recommendation(overall)
    }

    return Response(report, status=status.HTTP_200_OK)

from django.core.cache import cache

class JobAnalyticsView(APIView):
    throttle_classes = [PremiumThrottle]
    permission_classes = [IsAuthenticated, IsEmployer]

    def get(self, request, job_id):

        if not has_feature(request.user, "ANALYTICS"):
            raise PermissionDenied("Upgrade for analytics")

        return Response({
            "funnel": AnalyticsEngine.get_funnel(job_id),
            "conversion": AnalyticsEngine.conversion_ratio(job_id)
        })
    
class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")

        plan = SubscriptionPlan.objects.get(id=plan_id)

        order = create_order(plan.price)

        PaymentTransaction.objects.create(
            user=request.user,
            amount=plan.price,
            status="PENDING",
            payment_id=order["id"]
        )

        return Response(order)

class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        if verify_payment(data):
            txn = PaymentTransaction.objects.get(payment_id=data["razorpay_order_id"])
            txn.status = "SUCCESS"
            txn.save()

            plan = SubscriptionPlan.objects.get(price=txn.amount)

            UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                end_date=timezone.now() + timedelta(days=plan.duration_days)
            )

            return Response({"message": "Payment successful"})

        return Response({"error": "Payment failed"}, status=400)
    
class RevenueView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total = PaymentTransaction.objects.filter(
            status="SUCCESS"
        ).aggregate(total=Sum("amount"))

        return Response({
            "total_revenue": total["total"] or 0
        })
    
class MonthlyRevenueView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        data = PaymentTransaction.objects.filter(
            status="SUCCESS"
        ).annotate(
            month=TruncMonth("created_at")
        ).values("month").annotate(
            total=Sum("amount")
        ).order_by("month")

        return Response(data)
    
class TransactionsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        txns = PaymentTransaction.objects.all().order_by("-created_at")

        data = [
            {
                "user": t.user.email,
                "amount": t.amount,
                "status": t.status,
                "payment_id": t.payment_id,
                "date": t.created_at
            }
            for t in txns
        ]

        return Response(data)

class SubscriptionStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        data = UserSubscription.objects.values(
            "plan__name"
        ).annotate(
            count=Count("id")
        )

        return Response(data)

class CreateSubscriptionPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("DATA:", request.data)
        print("USER:", request.user)

        if request.user.role.upper() != "ADMIN":
            raise PermissionDenied("Only admin can create plans")

        data = request.data

        plan = SubscriptionPlan.objects.create(
            name=data.get("name"),
            price=data.get("price"),
            job_post_limit=data.get("job_post_limit", 0),
            has_ai_access=data.get("features", {}).get("ai_reports", False),
            has_analytics=data.get("features", {}).get("analytics", False),
            features=data.get("features", {}),
            duration_days=data.get("duration_days", 30)
        )

        return Response({
            "message": "Plan created",
            "plan_id": plan.id
        })

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get("amount")

        if not amount:
            return Response({"error": "Amount required"}, status=400)

        order = create_order(amount)

        return Response({
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"]
        })

class FailedPaymentsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        failed = PaymentTransaction.objects.filter(status="FAILED")

        data = [
            {
                "user": f.user.email,
                "amount": f.amount,
                "date": f.created_at
            }
            for f in failed
        ]

        return Response(data)
    
class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        plan_id = request.data.get("plan_id")

        if not plan_id:
            return Response({"error": "plan_id required"}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Invalid plan"}, status=404)

        start_date = timezone.now()
        end_date = start_date + timedelta(days=plan.duration_days)

        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            end_date=end_date
        )

        return Response({
            "message": "Subscription activated",
            "plan": plan.name,
            "valid_till": end_date
        })