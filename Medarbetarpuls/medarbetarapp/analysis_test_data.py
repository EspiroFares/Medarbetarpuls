from medarbetarapp.models import (
    Answer,
    SurveyResult,
    Question,
    Survey,
    CustomUser,
    UserRole,
)
import random

# kör raden nedan i shell för att lägga till objekt
# exec(open('medarbetarapp/analysis_test_data.py').read())
# Get the first SurveyResult instance

# removing old objects to avoid problems
Answer.objects.all().delete()
Question.objects.all().delete()
SurveyResult.objects.all().delete()

# -------- USER --------
# user = CustomUser.objects.first()

user, created = CustomUser.objects.get_or_create(
    email="admin@example.com",
    defaults={
        "name": "Admin User",
        "password": "admin123",  # gets hashed below
        "user_role": UserRole.ADMIN,
        "authorization_level": 10,
        "is_staff": True,
        "is_superuser": True,
    },
)

if created:
    user.set_password("admin123")  # must hash manually after creation
    user.save()
# -------- SURVEYS -------

survey = Survey.objects.create(
    name="Weekly Pulse Check",
    creator=user,
    deadline="2025-05-01 12:00:00",
    sending_date="2025-04-01 12:00:00",
)

r1 = SurveyResult.objects.create(published_survey=survey, user_id=1)
r2 = SurveyResult.objects.create(published_survey=survey, user_id=2)
r3 = SurveyResult.objects.create(published_survey=survey, user_id=3)
r4 = SurveyResult.objects.create(published_survey=survey, user_id=4)


# ----------- QUESTIONS -------------
q_text = Question.objects.create(
    question="1. What's one thing that made you smile today?",
    question_format="text",
    question_type="onetime",
)

q_yesno = Question.objects.create(
    question="2. Did you have a productive day?",
    question_format="yesno",
    question_type="onetime",
)

q_mc = Question.objects.create(
    question="3. Which of these activities did you enjoy at work today?",
    question_format="multiplechoice",
    question_type="onetime",
)

q_slider = Question.objects.create(
    question="4. On a scale of 1 to 10, how motivated are you feeling?",
    question_format="slider",
    question_type="onetime",
)

q_enps = Question.objects.create(
    question="How likely are you to recommend this company as a place to work?",
    question_format="slider",
    question_type="enps",
)

# ----------- ANSWERS R1 -------------
Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_text,
    free_text_answer="test.",
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_text,
    free_text_answer="test.",
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_text,
    free_text_answer="test.",
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_yesno,
    yes_no_answer=True,
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_mc,
    multiple_choice_answer=[True, False, True],  # Assumes 3 options for this question
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_slider,
    slider_answer=8.5,
)

# -----------ENPS-----------
Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=9.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=9.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=9.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=9.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=7.0,  # Passive
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=2.0,  # Detractor
)


Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=9.0,  # Promoter
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=7.5,  # Passive
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=6.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=5.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=3.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r1,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)


# ----------- ANSWERS R2 -------------
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_yesno,
    yes_no_answer=True,
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_mc,
    multiple_choice_answer=[True, False, True],  # Assumes 3 options for this question
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_slider,
    slider_answer=8.5,
)


# -----------ENPS-----------
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=2.0,  # Detractor
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=2.0,  # Detractor
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=2.0,  # Detractor
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=9.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=7.0,  # Passive
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=2.0,  # Detractor
)


Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=2.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=7.5,  # Passive
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=6.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=5.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=3.0,  # Detractor
)

Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)


# ----------- ANSWERS R3 -------------

Answer.objects.create(
    is_answered=True,
    survey=r3,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)
Answer.objects.create(
    is_answered=True,
    survey=r2,
    question=q_enps,
    slider_answer=10.0,  # Promoter
)

# ------- ANSWER R4 -----------
enps_scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
for i in range(10):
    Answer.objects.create(
        is_answered=True,
        survey=r4,
        question=q_enps,
        slider_answer=random.choice(enps_scores),
    )
