from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
# =========================
# VALIDATION
# =========================
def validate_resume(file):
    if not file.name.lower().endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed.")


# =========================
# CUSTOM USER
# =========================
class CustomUser(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        EMPLOYER = "EMPLOYER", "Employer"
        CANDIDATE = "CANDIDATE", "Candidate"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.email} - {self.role}"


# =========================
# CANDIDATE PROFILE
# =========================
class CandidateProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="candidate_profile"
    )

    skills = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    experience = models.IntegerField(default=0)

    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    resume = models.FileField(
        upload_to='resumes/',
        validators=[validate_resume],
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.email


# =========================
# EMPLOYER PROFILE
# =========================
class EmployerProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="employer_profile"
    )

    company_name = models.CharField(max_length=255)
    company_domain = models.CharField(max_length=255)
    company_size = models.CharField(max_length=100)

    verification_status = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.company_name


# =========================
# JOB MODEL
# =========================
class Job(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    class JobType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full Time"
        PART_TIME = "PART_TIME", "Part Time"
        INTERNSHIP = "INTERNSHIP", "Internship"
        REMOTE = "REMOTE", "Remote"

    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="jobs"
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    skills = models.TextField(blank=True, default="")

    experience = models.PositiveIntegerField(default=0)

    salary_min = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    location = models.CharField(max_length=150)

    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.FULL_TIME
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )


    shortlist_threshold = models.IntegerField(default=70)
    reject_threshold = models.IntegerField(default=40)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title


# =========================
# APPLICATION MODEL
# =========================
class Application(models.Model):

    STATUS_CHOICES = [
        ("APPLIED", "Applied"),
        ("SHORTLISTED", "Shortlisted"),
        ("INTERVIEW_SCHEDULED", "Interview Scheduled"),
        ("REJECTED", "Rejected"),
        ("SELECTED", "Selected"),
        ("CALL_QUEUED", "Call Queued"),
        ("IN_PROGRESS", "AI Call In Progress"),
        ("COMPLETED", "Completed"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)

    score = models.IntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="APPLIED"
    )

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("job", "candidate")

    def __str__(self):
        return f"{self.candidate} - {self.job} - {self.status}"


# =========================
# STATUS LOG
# =========================
class ApplicationStatusLog(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    old_status = models.CharField(max_length=30)
    new_status = models.CharField(max_length=30)

    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )


# =========================
# AI QUESTION ENGINE
# =========================
class AIQuestionTemplate(models.Model):

    CATEGORY_CHOICES = [
        ("INTRO", "Introduction"),
        ("EXP", "Experience"),
        ("SKILL", "Skills"),
        ("AVAIL", "Availability"),
        ("SALARY", "Salary"),
    ]

    text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    answer = models.TextField(blank=True, null=True)
    job_role = models.CharField(max_length=100, null=True, blank=True)
    min_experience = models.IntegerField(null=True, blank=True)
    required_skill = models.CharField(max_length=100, null=True, blank=True)

    order = models.IntegerField(default=0)

    # 🔥 AI FLOW
    expected_answer = models.CharField(max_length=100, null=True, blank=True)

    next_if_true = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="true_branch"
    )

    next_if_false = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="false_branch"
    )

    def __str__(self):
        return self.text[:50]


# =========================
# AI INTERVIEW SESSION
# =========================
class AIInterviewSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)

    current_question = models.ForeignKey(
        AIQuestionTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    current_index = models.IntegerField(default=0)

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# AI ANSWERS
# =========================
class AIAnswer(models.Model):
    session = models.ForeignKey(AIInterviewSession, on_delete=models.CASCADE)
    job = models.ForeignKey(
        "core.Job",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    question = models.ForeignKey(AIQuestionTemplate, on_delete=models.CASCADE)

    answer = models.TextField()
    relevance_score = models.FloatField(null=True, blank=True)
    completeness_score = models.FloatField(null=True, blank=True)
    keyword_score = models.FloatField(null=True, blank=True)
    final_score = models.FloatField(null=True, blank=True)

    ai_feedback = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


# =========================
# CALL LOG
# =========================
class CallLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

class AdminActionLog(models.Model):
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.email} - {self.action}"
    
class NotificationLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    status = models.CharField(max_length=20, default="SENT")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.status}"
    
# =========================
# INTERVIEW AVAILABILITY
# =========================
class AvailabilitySlot(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.date} {self.start_time} - {self.end_time}"


# =========================
# INTERVIEW SCHEDULE
# =========================
class InterviewSchedule(models.Model):

    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    slot = models.OneToOneField(AvailabilitySlot, on_delete=models.CASCADE)

    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate} - {self.job} - {self.scheduled_at}"
    
# =========================
# REMINDER LOG
# =========================
class ReminderLog(models.Model):

    STATUS_CHOICES = [
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    ]

    schedule = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=50)  # 24hr, 1hr, etc.

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(null=True, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.schedule} - {self.reminder_type} - {self.status}"
    
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)  # Free / Pro / Enterprise
    price = models.DecimalField(max_digits=10, decimal_places=2)
    job_post_limit = models.IntegerField(default=0)
    has_ai_access = models.BooleanField(default=False)
    has_analytics = models.BooleanField(default=False)
    features = models.JSONField(default=dict)
    duration_days = models.IntegerField(default=30)

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()


class PaymentTransaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=[
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed")
    ])

    payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BillingHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)