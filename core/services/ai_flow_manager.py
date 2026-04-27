from django.db.models import Q
from core.models import AIQuestionTemplate, AIAnswer


class AIFlowManager:

    def __init__(self, session):
        self.session = session
        self.user = session.user
        self.job = session.job

    # 🎯 MAIN FUNCTION
    def get_next_question(self):

        questions = self.get_filtered_questions()

        if self.session.current_index >= len(questions):
            self.session.is_completed = True
            self.session.save()
            return None

        return questions[self.session.current_index]

    # 🧠 INTELLIGENCE ENGINE
    def get_filtered_questions(self):

        qs = AIQuestionTemplate.objects.all().order_by("order")

        # 🔥 Role-based filtering
        if self.job.title:
            qs = qs.filter(Q(job_role__isnull=True) | Q(job_role=self.job.title))

        profile = getattr(self.user, "candidate_profile", None)

        filtered = []

        for q in qs:

            # Experience condition
            if q.min_experience:
                if not profile or profile.experience < q.min_experience:
                    continue

            # Skill condition
            if q.required_skill:
                if not profile or q.required_skill.lower() not in profile.skills.lower():
                    continue

            filtered.append(q)

        return filtered

    # 💾 SAVE ANSWER
    def save_answer(self, question, answer):

        AIAnswer.objects.create(
            session=self.session,
            question=question,
            answer=answer
        )

        self.session.current_index += 1
        self.session.save()