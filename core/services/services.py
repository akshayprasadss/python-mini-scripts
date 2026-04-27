from django.db.models import Count
from django.core.mail import send_mail
from core.models import (
    Job,
    Application,
    ApplicationStatusLog,
    NotificationLog
)

# ==============================
# JOB SERVICE
# ==============================
class JobService:

    @staticmethod
    def get_queryset_for_user(user):
        queryset = (
            Job.objects
            .select_related("employer", "employer__user")
            .annotate(application_count=Count("application_set"))
        )

        if user.is_authenticated and user.role == "EMPLOYER":
            return queryset.filter(employer=user.employer_profile)

        return queryset.filter(status="OPEN")


# ==============================
# ATS MATCHING SERVICE
# ==============================
def calculate_match_score(candidate_skills, job_skills, candidate_exp=0, job_exp=0):

    job_set = set([s.lower().strip() for s in job_skills.split(",") if s.strip()])
    candidate_set = set([s.lower().strip() for s in candidate_skills if s.strip()])

    matched = candidate_set.intersection(job_set)
    missing = job_set - candidate_set

    # 70% skill weight
    skill_score = 0
    if len(job_set) > 0:
        skill_score = (len(matched) / len(job_set)) * 70

    # 30% experience weight
    exp_score = 0
    if job_exp > 0:
        exp_score = min(candidate_exp / job_exp, 1) * 30

    total_score = int(skill_score + exp_score)
    

    return total_score, list(matched), list(missing)


# ==============================
# EMAIL + LOGGING SERVICE
# ==============================
def send_email_notification(subject, message, recipient_user):
    print("🔥 EMAIL FUNCTION CALLED:", recipient_user.email)
    try:
        send_mail(
            subject,
            message,
            "akshayprasad014@gmail.com",
            [recipient_user.email],
        )

        NotificationLog.objects.create(
            user=recipient_user,
            message=message,
            status="SENT"
        )

    except Exception as e:
        NotificationLog.objects.create(
            user=recipient_user,
            message=str(e),
            status="FAILED"
        )


# ==============================
# AUTO SHORTLISTING ENGINE
# ==============================
def auto_process_application(application):

    job = application.job
    candidate = application.candidate

    print("===== AUTO PROCESS START =====")

    # get candidate skills
    candidate_skills = candidate.skills.split(",") if candidate.skills else []
    print("Candidate skills:", candidate_skills)

    print("Job skills:", job.skills)
    print("Candidate experience:", candidate.experience)
    print("Job experience:", job.experience)

    # calculate ATS score
    score, matched, missing = calculate_match_score(
        candidate_skills,
        job.skills,
        candidate.experience,
        job.experience
    )

    print("Score:", score)
    print("Matched skills:", matched)
    print("Missing skills:", missing)

    print("Shortlist threshold:", job.shortlist_threshold)
    print("Reject threshold:", job.reject_threshold)

    # skip if already processed
    if application.status != "APPLIED":
        print("Skipped: Already processed")
        return

    # threshold decision
    if score >= job.shortlist_threshold:
        new_status = "SHORTLISTED"
        print("Decision: SHORTLISTED")

    elif score < job.reject_threshold:
        new_status = "REJECTED"
        print("Decision: REJECTED")

    else:
        print("Decision: STILL APPLIED (score in between)")
        return

    old_status = application.status
    application.status = new_status
    application.save()

    print("Status updated from", old_status, "to", new_status)

    # 🔥 SEND EMAIL
    send_email_notification(
        subject="Application Update",
        message=f"Your application has been {new_status}",
        recipient_user=application.candidate.user
    )

    print("Email sent")

    # log timeline
    ApplicationStatusLog.objects.create(
        application=application,
        old_status=old_status,
        new_status=new_status,
        changed_by=None
    )

    print("Log created")
    print("===== AUTO PROCESS END =====")