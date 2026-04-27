from core.models import AIQuestionTemplate, AIAnswer


class QuestionEngine:

    def __init__(self, session):
        self.session = session
        self.job = session.job
        self.candidate = session.candidate

    def get_filtered_questions(self):
        questions = AIQuestionTemplate.objects.all().order_by("order")
        answers = AIAnswer.objects.filter(session=self.session)

        filtered = []

        for q in questions:

            # Skill filtering
            if q.required_skill:
                if not self.job.required_skills:
                    continue
                if q.required_skill.lower() not in self.job.required_skills.lower():
                    continue

            # Experience filtering
            if q.min_experience:
                if not hasattr(self.candidate, "experience"):
                    continue
                if self.candidate.experience < q.min_experience:
                    continue

            # Dynamic condition (example)
            if q.category == "SALARY":
                if any("not interested" in a.answer.lower() for a in answers):
                    continue

            filtered.append(q)

        return filtered

    def get_next_question(self):
        questions = self.get_filtered_questions()
        index = self.session.current_question_index

        if index >= len(questions):
            self.session.is_completed = True
            self.session.save()
            return None

        return questions[index]

    def submit_answer(self, question, answer_text):
        AIAnswer.objects.create(
            session=self.session,
            question=question,
            answer=answer_text
        )

        self.session.current_question_index += 1
        self.session.save()