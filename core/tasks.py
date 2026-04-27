from celery import shared_task
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from celery.schedules import crontab
import time
from core.services.reminder_engine import ReminderEngine
import logging
from core.services.email import send_email_notification
from core.services.eligibility import check_ai_call_eligibility
from core.services.ai_bridge import AIBridgeService
from core.models import (
    AIInterviewSession,
    AIQuestionTemplate,
    AIAnswer,
    Application,
)
logger = logging.getLogger(__name__)

# ===============================
# 1. AI TASK (Already done)
# ===============================
@shared_task
def process_ai_call(application_id):
    logger.info("📞 AI Call Started...")

    try:
        application = Application.objects.get(id=application_id)

        ai = AIBridgeService()

        prompts = [
            "Tell me about yourself",
            "What is Django?",
            "Explain REST API"
        ]

        for prompt in prompts:
            # STEP 1: Generate AI question
            question = ai.generate_question(prompt)
            logger.warning(f"AI Question: {question}")

            # STEP 2: Convert to speech (simulate)
            audio = ai.text_to_speech(question)

            # STEP 3: Candidate response (simulate STT)
            answer = ai.speech_to_text(audio)
            logger.warning(f"Candidate Answer: {answer}")

            time.sleep(2)

        logger.info("✅ AI Processing Done")

    except Exception as e:
        logger.error(f"❌ AI Call Failed: {str(e)}")

# ===============================
# 2. EMAIL TASK (NEW 🔥)
# ===============================

@shared_task
def send_email_task(subject, message, email):
    send_mail(
        subject,
        message,
        "akshayprasad014@gmail.com",
        [email],
        fail_silently=False
    )

# ===============================
# 3. RESUME PARSE TASK (NEW 🔥)
# ===============================
@shared_task
def parse_resume_task(application_id):
    logger.info("📄 Resume parsing started")

    time.sleep(3)  # simulate parsing

    logger.info("✅ Resume parsed successfully")

@shared_task
def delete_old_applications():
    print("🧹 Running cleanup task...")

    old_time = timezone.now() - timedelta(days=30)

    deleted_count, _ = Application.objects.filter(
        created_at__lt=old_time
    ).delete()

    print(f"✅ Deleted {deleted_count} old applications")

@shared_task
def auto_trigger_ai_calls():
    applications = Application.objects.filter(status="APPLIED")

    for app in applications:
        if check_ai_call_eligibility(app):
            app.status = "CALL_QUEUED"
            app.save()

            process_ai_call.delay(app.id)

@shared_task
def run_reminder_engine():
    from core.services.reminder_engine import ReminderEngine  # lazy import
    ReminderEngine.process_reminders()