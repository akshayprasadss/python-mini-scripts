from core.models import AIQuestionTemplate, AIAnswer, AIInterviewSession


class AIEngine:

    @staticmethod
    def get_first_question(job):
        """
        Get first question for a job
        """
        return AIQuestionTemplate.objects.filter(
            job_role__icontains=job.title
        ).order_by("order").first()


    @staticmethod
    def evaluate_answer(question, answer_text):
        """
        Simple evaluation (can upgrade with AI later)
        """
        if not question.expected_answer:
            return True  # no condition → always true

        return question.expected_answer.lower() in answer_text.lower()


    @staticmethod
    def get_next_question(question, is_correct):
        """
        Branching logic
        """
        if is_correct:
            return question.next_if_true
        else:
            return question.next_if_false


    @staticmethod
    def process_answer(session, question, answer_text):
        """
        Main engine logic
        """
        # Save answer
        AIAnswer.objects.create(
            session=session,
            question=question,
            answer=answer_text
        )

        # Evaluate
        is_correct = AIEngine.evaluate_answer(question, answer_text)

        # Get next question
        next_question = AIEngine.get_next_question(question, is_correct)

        # Update session
        if next_question:
            session.current_question = next_question
        else:
            session.is_completed = True

        session.save()

        return next_question