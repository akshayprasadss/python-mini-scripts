class ScoringEngine:

    @staticmethod
    def evaluate(answer, question):
        answer = answer.lower()

        # ✅ 1. Keyword Matching
        keywords = []
        if question.required_skill:
            keywords.append(question.required_skill.lower())

        keyword_matches = sum(1 for k in keywords if k in answer)
        keyword_score = keyword_matches * 10

        # ✅ 2. Relevance (simple logic)
        relevance_score = 10 if keywords and keyword_matches > 0 else 5

        # ✅ 3. Completeness (based on length)
        word_count = len(answer.split())

        if word_count > 20:
            completeness_score = 10
        elif word_count > 10:
            completeness_score = 7
        else:
            completeness_score = 4

        # ✅ 4. Final Score (weighted)
        final_score = (
            keyword_score * 0.4 +
            relevance_score * 0.3 +
            completeness_score * 0.3
        )

        return {
            "keyword_score": keyword_score,
            "relevance_score": relevance_score,
            "completeness_score": completeness_score,
            "final_score": round(final_score, 2),
            "feedback": "Good answer" if final_score > 7 else "Needs improvement"
        }