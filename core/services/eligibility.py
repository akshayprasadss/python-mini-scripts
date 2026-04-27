def check_ai_call_eligibility(application):
    """
    Returns True if candidate is eligible for AI call
    """

    # Rule 1: Score threshold
    if not application.score or application.score < 60:
        return False

    # Rule 2: Already processed
    if application.status not in ["APPLIED", "SHORTLISTED", "ELIGIBLE"]:
        return False

    # Rule 3: Candidate availability (simple version)
    # You can later add time slots
    return True