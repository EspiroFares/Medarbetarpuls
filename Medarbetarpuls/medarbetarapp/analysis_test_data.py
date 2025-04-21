from http.client import MULTIPLE_CHOICES
from medarbetarapp.models import (
    Answer,
    QuestionFormat,
    QuestionType,
    SurveyUserResult,
    Question,
    Survey,
    CustomUser,
    UserRole,
    MultipleChoiceQuestion,
    YesNoQuestion,
    EmployeeGroup,
    EmailList,
    Organization,
)
import random

# kör raden nedan i shell för att lägga till objekt
# exec(open('medarbetarapp/analysis_test_data.py').read())
# om ni kör raden ovan flera gånger kommer django skapa nya objekt med nya id'n. Vill ni komma åt ett specifikt objekt med samma id hela tiden behöver ni då flusha databasen emellan körningar. Detta kan göras med kommandot:
# python manage.py flush

# HELPER FUNCTIONS
# Creates answer object connected to a specific SurveyUserResult


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
    users = []
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
        users.append(user)
    return users


def createSurveys(amount: int, surveyCreator: CustomUser):
    if surveyCreator.user_role != UserRole.SURVEY_CREATOR:
        print(
            f"UserRole in createSurveys is a {surveyCreator.user_role} but needs to be a {UserRole.SURVEY_CREATOR}. "
        )
        return
    surveys = []
    deadlines = [
        "2025-01-01 12:00:00",
        "2025-02-01 12:00:00",
        "2025-03-01 12:00:00",
        "2025-04-01 12:00:00",
        "2025-05-01 12:00:00",
        "2025-06-01 12:00:00",
        "2025-07-01 12:00:00",
        "2025-08-01 12:00:00",
        "2025-09-01 12:00:00",
        "2025-10-01 12:00:00",
    ]
    for i in range(amount):
        survey = Survey.objects.create(
            name=f"Weekly Pulse Check {i}",
            creator=surveyCreator,
            deadline=deadlines[i],
            sending_date="2025-01-01 10:00:00",
        )
        surveys.append(survey)
    return surveys


def createSurveyUserResult(amount: int, survey: Survey, user: CustomUser):
    results = []
    for i in range(amount):
        result = SurveyUserResult.objects.create(
            published_survey=survey, user_id=user.id
        )
        results.append(result)
    return results


def createQuestions(
    amount: int,
    questionFormat: QuestionFormat,
    questionType: QuestionType,
    survey: Survey,
):
    result = []
    questions = []
    if questionFormat == QuestionFormat.MULTIPLE_CHOICE:
        questions = [
            "Which of these activities did you enjoy at work today?",
            "Which tools did you use most during your work today?",
            "What type of task did you spend the most time on?",
            "Which team(s) did you collaborate with today?",
            "Which of these break activities helped you recharge today?",
        ]
    elif questionFormat == QuestionFormat.YES_NO:
        questions = [
            "Did you have a productive day?",
            "Did you feel supported by your team today?",
            "Did you encounter any blockers during your tasks?",
            "Did you receive feedback on your work today?",
            "Did you take enough breaks throughout the day?",
        ]

    elif questionFormat == QuestionFormat.TEXT:
        questions = [
            "Do you have any suggestions for future projects?",
            "What was the highlight of your day?",
            "Is there anything you’d like to improve in your workflow?",
            "What’s one thing you learned today?",
            "Any feedback for your manager or team?",
        ]

    elif questionFormat == QuestionFormat.SLIDER:
        questions = [
            "On a scale of 1 to 10, how motivated are you feeling?",
            "Rate your stress level today (1 being relaxed, 10 being stressed).",
            "How focused were you during your work today?",
            "How satisfied are you with your accomplishments today?",
            "How would you rate your energy level throughout the day?",
        ]

    if questionType == QuestionType.ENPS:
        questions = ["How likely are you to recommend this company as a place to work?"]
        amount = 1
        questionFormat = QuestionFormat.SLIDER

    for i in range(amount):
        q = Question.objects.create(
            question=random.choice(questions),
            question_format=questionFormat,
            question_type=questionType,
        )
        if q.question_format == QuestionFormat.MULTIPLE_CHOICE:
            mcq = MultipleChoiceQuestion.objects.create(
                question_format=QuestionFormat.MULTIPLE_CHOICE,
                options=["A", "B", "C", "D"],
            )
            q.multiple_choice_question = mcq
            q.save()
        elif q.question_format == QuestionFormat.YES_NO:
            ynq = YesNoQuestion.objects.create(
                question_format=QuestionFormat.YES_NO,
            )
            q.yes_no_question = ynq
            q.save()
        result.append(q)
    return result


def createAnswers(amount: int, result: SurveyUserResult, question: Question):
    scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    answers = []
    for i in range(amount):
        if question.question_format == QuestionFormat.MULTIPLE_CHOICE:
            num_options = len(question.specific_question.options)
            answer_data = [random.choice([True, False]) for j in range(num_options)]
            a = Answer.objects.create(
                is_answered=True,
                survey=result,
                question=question,
                multiple_choice_answer=answer_data,
            )
        elif question.question_format == QuestionFormat.SLIDER:
            a = Answer.objects.create(
                is_answered=True,
                survey=result,
                question=question,
                slider_answer=random.choice(scores),
            )
        elif question.question_format == QuestionFormat.YES_NO:
            a = Answer.objects.create(
                is_answered=True,
                survey=result,
                question=question,
                yes_no_answer=random.choice([True, False]),
            )
        answers.append(a)
    return answers


# -------------------------------------------------


# Clean up related models to avoid duplicates
Answer.objects.all().delete()
Question.objects.all().delete()
SurveyUserResult.objects.all().delete()
Survey.objects.all().delete()
CustomUser.objects.all().delete()
EmployeeGroup.objects.all().delete()
EmailList.objects.all().delete()
Organization.objects.all().delete()

# ----- CREATE MOCK ORGANISATION WITH USERS -----
org = Organization.objects.create(name="TestOrg")

admin = createUsers(UserRole.ADMIN, 1)[0]
admin.admin = org
admin.is_staff = True
admin.is_superuser = True
admin.save()

survey_creator = createUsers(UserRole.SURVEY_CREATOR, 1)[0]
survey_creator.admin = org
survey_creator.is_staff = True
survey_creator.save()

survey_responders = createUsers(UserRole.SURVEY_RESPONDER, 4)
for r in survey_responders:
    r.admin = org
    r.save()

# ----- EMPLOYEE GROUPS -----
base_group = EmployeeGroup.objects.create(name="Alla", organization=org)
dev_team = EmployeeGroup.objects.create(name="hr", organization=org)

# Assign users to employee groups
base_group.employees.add(admin, survey_creator, *survey_responders)
dev_team.employees.add(*survey_responders)

# Admin manages both groups
base_group.managers.add(admin)
dev_team.managers.add(admin)

# ----- EMAIL LIST (for account validation flow) -----
for user in [admin, survey_creator, *survey_responders]:
    email_entry = EmailList.objects.create(email=user.email, org=org)
    email_entry.employee_groups.add(base_group)
    email_entry.save()

# ----- CREATE SURVEYS AND QUESTIONS -----
surveys = createSurveys(3, survey_creator)

question_enps = createQuestions(1, QuestionFormat.SLIDER, QuestionType.ENPS, surveys[0])
question_mc = createQuestions(
    1, QuestionFormat.MULTIPLE_CHOICE, QuestionType.REOCCURRING, surveys[0]
)

question_yn = createQuestions(
    1, QuestionFormat.YES_NO, QuestionType.REOCCURRING, surveys[0]
)
all_questions = question_mc + question_enps + question_yn

for s in surveys:
    for q in all_questions:
        q.connected_surveys.add(s)

    for r in survey_responders:
        survey_result = createSurveyUserResult(1, s, r)
        for sr in survey_result:
            for q in all_questions:
                createAnswers(1, sr, q)

print("✅ Test organization and users created successfully!")
