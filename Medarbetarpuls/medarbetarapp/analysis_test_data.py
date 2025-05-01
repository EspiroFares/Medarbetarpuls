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
    SliderQuestion,
    TextQuestion,
    EmployeeGroup,
    EmailList,
    Organization,
)
import random
from django.utils import timezone

# kör raden nedan i shell för att lägga till objekt
# exec(open('medarbetarapp/analysis_test_data.py').read())
# om ni kör raden ovan flera gånger kommer django skapa nya objekt med nya id'n. Vill ni komma åt ett specifikt objekt med samma id hela tiden behöver ni då flusha databasen emellan körningar. Detta kan göras med kommandot:
# python manage.py flush


Answer.objects.all().delete()
Question.objects.all().delete()
SurveyUserResult.objects.all().delete()
Survey.objects.all().delete()
CustomUser.objects.all().delete()
EmployeeGroup.objects.all().delete()
EmailList.objects.all().delete()
Organization.objects.all().delete()


def createUsers(userRole: UserRole, amount: int):
    first_names = ["Hannah", "Liam", "Ava", "Noah", "Sophia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
    users = []
    for i in range(amount):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name}{last_name}{i}@example.com"
        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "name": f"{first_name} {last_name}",
                "password": "123",
                "user_role": userRole,
                "authorization_level": 10,
                "is_staff": userRole != UserRole.SURVEY_RESPONDER,
                "is_superuser": userRole == UserRole.ADMIN,
            },
        )
        if created:
            user.set_password("123")
            user.save()
        users.append(user)
    return users


def createSurveys(amount: int, surveyCreator: CustomUser):
    surveys = []
    for i in range(amount):
        survey = Survey.objects.create(
            name=f"Weekly Pulse Check {i}",
            creator=surveyCreator,
            deadline=f"2024-12-{(i % 28) + 1} 12:00:00",
            sending_date=f"2024-11-{(i % 28) + 1} 10:00:00",
            last_notification=timezone.now(),
            collected_answer_count=0,
            published_count=0,
            is_viewable=True,
            is_anonymous=True,
        )
        target_group = EmployeeGroup.objects.get(name="IT")
        survey.employee_groups.add(target_group)
        surveys.append(survey)
    return surveys


def createQuestions(
    amount: int,
    questionFormat: QuestionFormat,
    questionType: QuestionType,
    survey: Survey,
):
    result = []
    text_pool = {
        QuestionFormat.MULTIPLE_CHOICE: "Which tool did you use most today?",
        QuestionFormat.SLIDER: "How motivated are you feeling today?",
        QuestionFormat.YES_NO: "Did you enjoy your workday?",
        QuestionFormat.TEXT: "Any comments about your day?",
    }
    enps_prompt = "How likely are you to recommend this company as a place to work?"

    for i in range(amount):
        if (
            questionType == QuestionType.ENPS
            and questionFormat == QuestionFormat.SLIDER
        ):
            question_text = enps_prompt
        else:
            question_text = text_pool.get(questionFormat, "")

        q = Question.objects.create(
            question=question_text,
            question_format=questionFormat,
            question_type=questionType,
        )
        if questionFormat == QuestionFormat.MULTIPLE_CHOICE:
            mcq = MultipleChoiceQuestion.objects.create(
                options=["Option A", "Option B", "Option C"],
                question_format=QuestionFormat.MULTIPLE_CHOICE,
            )
            q.multiple_choice_question = mcq

        elif questionFormat == QuestionFormat.SLIDER:
            sq = SliderQuestion.objects.create(
                min_interval=1,
                max_interval=10,
                min_text="Bad",
                max_text="Great",
                question_format=QuestionFormat.SLIDER,
            )
            q.slider_question = sq
        elif questionFormat == QuestionFormat.YES_NO:
            ynq = YesNoQuestion.objects.create(
                question_format=QuestionFormat.YES_NO,
            )
            q.yes_no_question = ynq
        elif questionFormat == QuestionFormat.TEXT:
            tq = TextQuestion.objects.create(
                question_format=QuestionFormat.TEXT,
            )
            q.text_question = tq
        q.save()
        q.connected_surveys.add(survey)
        survey.questions.add(q)
        survey.save()
        result.append(q)
    return result


def createAnswers(result: SurveyUserResult, question: Question):
    if question.question_format == QuestionFormat.MULTIPLE_CHOICE:
        Answer.objects.create(
            is_answered=True,
            survey=result,
            question=question,
            multiple_choice_answer=[True, False, False],
        )
    elif question.question_format == QuestionFormat.SLIDER:
        Answer.objects.create(
            is_answered=True,
            survey=result,
            question=question,
            slider_answer=random.randint(1, 10),
        )
    elif question.question_format == QuestionFormat.YES_NO:
        Answer.objects.create(
            is_answered=True,
            survey=result,
            question=question,
            yes_no_answer=random.choice([True, False]),
        )
    elif question.question_format == QuestionFormat.TEXT:
        Answer.objects.create(
            is_answered=True,
            survey=result,
            question=question,
            free_text_answer="This is a comment",
        )


org = Organization.objects.create(name="TestOrg")
admin = createUsers(UserRole.ADMIN, 1)[0]
admin.admin = org
admin.save()
creator = createUsers(UserRole.SURVEY_CREATOR, 1)[0]
creator.admin = org
creator.save()
responders = createUsers(UserRole.SURVEY_RESPONDER, 8)
for r in responders:
    r.admin = org
    r.save()


base_group = EmployeeGroup.objects.create(name="Alla", organization=org)
hr_team = EmployeeGroup.objects.create(name="HR", organization=org)
it_team = EmployeeGroup.objects.create(name="IT", organization=org)
base_group.employees.add(admin, creator, *responders)
hr_team.employees.add(*responders[:4])
it_team.employees.add(*responders[4:])
base_group.managers.add(admin)
hr_team.managers.add(admin)
it_team.managers.add(admin)


for user in [admin, creator, *responders]:
    email_entry = EmailList.objects.create(email=user.email, org=org)
    email_entry.employee_groups.add(base_group)
    email_entry.save()


surveys = createSurveys(3, creator)
questions = []
for s in surveys:
    questions += createQuestions(1, QuestionFormat.SLIDER, QuestionType.ENPS, s)
    questions += createQuestions(
        1, QuestionFormat.MULTIPLE_CHOICE, QuestionType.REOCCURRING, s
    )
    questions += createQuestions(1, QuestionFormat.YES_NO, QuestionType.REOCCURRING, s)
    questions += createQuestions(1, QuestionFormat.TEXT, QuestionType.REOCCURRING, s)

for s in surveys:
    s.publish_survey()
    for result in s.survey_results.all():
        for q in s.questions.all():
            createAnswers(result, q)

print("✅ Successfully created test data!")
