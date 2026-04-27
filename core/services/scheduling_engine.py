from datetime import datetime
from django.utils import timezone
from core.models import AvailabilitySlot, InterviewSchedule

class SchedulingEngine:

    @staticmethod
    def book_slot(candidate, job, slot_id):

        # 1. Get slot
        try:
            slot = AvailabilitySlot.objects.get(id=slot_id)
        except AvailabilitySlot.DoesNotExist:
            raise Exception("Slot not found")

        # 2. Check already booked
        if slot.is_booked:
            raise Exception("Slot already booked")

        # 3. Time validation (no past booking)
        slot_datetime = timezone.make_aware(
            datetime.combine(slot.date, slot.start_time)
        )
        if slot_datetime < timezone.now():
            raise Exception("Cannot book past slot")

        # 4. Conflict check (candidate already has interview at same time)
        exists = InterviewSchedule.objects.filter(
            candidate=candidate,
            scheduled_at=slot_datetime,
            status="SCHEDULED"
        ).exists()

        if exists:
            raise Exception("You already have interview at this time")

        # 5. Create schedule
        schedule = InterviewSchedule.objects.create(
            candidate=candidate,
            job=job,
            slot=slot,
            scheduled_at=slot_datetime
        )

        # 6. Mark slot booked
        slot.is_booked = True
        slot.save()

        return schedule