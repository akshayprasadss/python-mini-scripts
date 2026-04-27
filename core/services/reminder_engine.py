from django.utils import timezone
from datetime import timedelta
from core.models import InterviewSchedule, ReminderLog


class ReminderEngine:

    @staticmethod
    def send_reminder(schedule, reminder_type):

        # ✅ lazy import (FIXES circular import)
        from core.tasks import send_email_task

        # ❗ Prevent duplicate reminders
        already_sent = ReminderLog.objects.filter(
            schedule=schedule,
            reminder_type=reminder_type
        ).exists()

        if already_sent:
            return

        try:
            message = f"Reminder: Your interview is scheduled at {schedule.scheduled_at}"

            send_email_task.delay(
                subject="Interview Reminder",
                message=message,
                email=schedule.candidate.user.email
            )

            ReminderLog.objects.create(
                schedule=schedule,
                user=schedule.candidate.user,   # ✅ YOU MISSED THIS (important)
                reminder_type=reminder_type,
                status="SENT"
            )

        except Exception as e:
            ReminderLog.objects.create(
                schedule=schedule,
                user=schedule.candidate.user,   # ✅ REQUIRED FIELD
                reminder_type=reminder_type,
                status="FAILED"
            )
    @staticmethod
    def process_reminders():

        now = timezone.now()

        upcoming = InterviewSchedule.objects.filter(
            status="SCHEDULED",
            scheduled_at__gte=now,
            scheduled_at__lte=now + timedelta(hours=24)
        )

        for schedule in upcoming:

            time_diff = schedule.scheduled_at - now

            # ✅ DEBUG LINE (ADD HERE)
            print(f"Checking schedule: {schedule.id}, time_diff: {time_diff}")

            # 🔔 24 hour reminder
            if timedelta(hours=22) < time_diff <= timedelta(hours=24):
                ReminderEngine.send_reminder(schedule, "24hr")

            # 🔔 1 hour reminder
            elif timedelta(minutes=45) < time_diff <= timedelta(hours=1):
                ReminderEngine.send_reminder(schedule, "1hr")