from core.models import Application, AIAnswer, CandidateProfile


def calculate_overall(ats, ai):
    return round((ats * 0.4) + (ai * 0.6), 2)


def get_ats_score(candidate):
    applications = Application.objects.filter(candidate=candidate)

    if not applications.exists():
        return 50  # default score

    return sum([app.score or 50 for app in applications]) / applications.count()


def get_ai_score(candidate):
    answers = AIAnswer.objects.filter(session__user=candidate.user)

    if not answers.exists():
        return 50

    return sum([a.final_score or 0 for a in answers]) / answers.count()


def generate_strengths(candidate):
    strengths = []

    if candidate.experience >= 2:
        strengths.append("Good experience level")

    if candidate.skills:
        strengths.append("Has relevant technical skills")

    return strengths


def generate_risks(candidate):
    risks = []

    if candidate.experience < 1:
        risks.append("Fresher level candidate")

    if not candidate.skills:
        risks.append("Skills not clearly defined")

    return risks


def generate_summary(name, score):
    if score > 80:
        return f"{name} is highly recommended."
    elif score > 60:
        return f"{name} is suitable for shortlist."
    return f"{name} is not recommended."


def get_recommendation(score):
    if score > 80:
        return "Shortlist"
    elif score > 60:
        return "Hold"
    return "Reject"