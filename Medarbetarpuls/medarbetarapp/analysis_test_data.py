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
# om ni kör raden ovan flera gånger kommer django skapa nya objekt med nya id'n. Vill ni komma åt ett specifikt objekt med samma id hela tiden behöver ni då flusha databasen emellan körningar. Detta kan göras med kommandot:
# python manage.py flush


# removing old objects to avoid problems
Answer.objects.all().delete()
Question.objects.all().delete()
SurveyResult.objects.all().delete()
Survey.objects.all().delete()

yesno_questions = ["Did you have a productive day?"]


# HELPER FUNCTIONS
# Creates answer object connected to a specific SurveyResult
def createENPSAnswers(amount: int, result: SurveyResult):
    enps_scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for i in range(amount):
        Answer.objects.create(
            is_answered=True,
            survey=result,
            question=q_enps,
            slider_answer=random.choice(enps_scores),
        )
    return


def createUsers(
    userRole: UserRole,
    amount: int,
):
    first_names = [
        "Hannah",
        "Liam",
        "Ava",
        "Noah",
        "Sophia",
        "Mason",
        "Isabella",
        "Ethan",
        "Mia",
        "Logan",
        "Charlotte",
        "Lucas",
        "Amelia",
        "Jackson",
        "Harper",
    ]
    last_names = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
        "Hernandez",
        "Lopez",
        "Gonzalez",
        "Wilson",
        "Anderson",
    ]
    result = []
    if userRole == UserRole.ADMIN:
        isStaff = True
        isSuperUser = True
    elif userRole == UserRole.SURVEY_CREATOR:
        isStaff = True
        isSuperUser = False
    elif userRole == UserRole.SURVEY_RESPONDER:
        isStaff = False
        isSuperUser = False
    for i in range(amount):
        # maybe add something here so we dont get the same combination multiple times?
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        user, created = CustomUser.objects.get_or_create(
            email=f"{first_name}{last_name}@example.com",
            defaults={
                "name": f"{first_name} {last_name}",
                "password": f"{first_name}123",
                "user_role": userRole,
                "authorization_level": 10,  # vet inte vad jag ska sätta här?
                "is_staff": isStaff,
                "is_superuser": isSuperUser,
            },
        )
        if created:
            user.set_password("123")  #
            user.save()
        result.append(user)
    return result


def createSurveys(amount: int, surveyCreator: CustomUser):
    if surveyCreator.user_role != UserRole.SURVEY_CREATOR:
        print(
            f"UserRole in createSurveys is a {surveyCreator.user_role} but needs to be a {UserRole.SURVEY_CREATOR}. "
        )
        return
    surveys = []
    for i in range(amount):
        survey = Survey.objects.create(
            name=f"Weekly Pulse Check {i}",
            creator=surveyCreator,
            deadline="2025-07-01 12:00:00",
            sending_date="2025-06-01 12:00:00",
        )
        surveys.append(survey)
    return surveys


def createSurveyResult(amount: int, survey: Survey):
    results = []
    for i in range(amount):
        result = SurveyResult.objects.create(published_survey=survey)
        results.append(result)
    return results


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
