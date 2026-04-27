import logging

logger = logging.getLogger(__name__)


# ==========================================
# 1. CALCULATE MATCH SCORE (ATS)
# ==========================================
def calculate_match_score(application):
    """
    Calculate ATS score for a candidate.
    This is a dummy logic (you can improve later).
    """

    logger.info("📊 Calculating match score...")

    # Dummy scoring logic
    score = 0

    # Example conditions (you can extend later)
    if application.candidate:
        score += 30

    if application.job:
        score += 30

    # Assume resume exists (future improvement)
    score += 40

    logger.info(f"✅ Match Score: {score}")

    return score


# ==========================================
# 2. AUTO PROCESS APPLICATION
# ==========================================
def auto_process_application(application):
    """
    Automatically process application after applying.
    This connects ATS + eligibility + AI trigger.
    """

    logger.info("⚙️ Auto processing application...")

    # Step 1: Calculate score
    score = calculate_match_score(application)
    application.score = score

    # Step 2: ATS decision
    if score >= 60:
        application.status = "SHORTLISTED"
        logger.info("✅ Candidate shortlisted")
    else:
        application.status = "REJECTED"
        logger.info("❌ Candidate rejected")

    application.save()

    return application


# ==========================================
# 3. JOB SERVICE (OPTIONAL - ADVANCED)
# ==========================================
class JobService:
    """
    Service class for job-related operations
    """

    @staticmethod
    def process_application(application):
        """
        Wrapper method to process application
        """
        return auto_process_application(application)