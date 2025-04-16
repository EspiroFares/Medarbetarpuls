from medarbetarapp.models import *

# exec(open('medarbetarapp/view_db.py').read())
# Count total objects
print("Answers:", Answer.objects.count())
print("Questions:", Question.objects.count())
print("Surveys:", Survey.objects.count())
print("SurveyUserResults:", SurveyUserResult.objects.count())
print("\n")
# View some actual entries
# print("\nSome Answers:")
# for a in Answer.objects.all()[:5]:
#    print(a.free_text_answer, a.is_answered)

# print("\nSome Questions:")
# for q in Question.objects.all()[:5]:
#   print(q.question, q.question_format)

for q in Question.objects.filter(question_format=QuestionFormat.YES_NO):
    if q.specific_question:
        print(f"Question: {q.question}")
        print("-" * 40)

for u in CustomUser.objects.all():
    print(f"Name: {u.name}")
print("-" * 40)
for s in Survey.objects.all():
    print(f"Survey ID: {s.id}, Name: {s.name}")
print("-" * 40)

print(type(SurveyUserResult.objects.filter(published_survey=Survey.objects.first())))
count = 0
for s in Survey.objects.all():
    print("-" * 40)
    print(f"Survey ID:{count} \n")
    for j in SurveyUserResult.objects.filter(published_survey=s):
        print(f"Survey User Result :{j.user} \n")
    count += 1
    print("-" * 40)
print("\n")

answers = Answer.objects.all()
for a in Answer.objects.all():
    print(f"Answer: {a}")
for q in Question.objects.all():
    print(f"Question: {q.question} Survey: {q.connected_surveys}")
# print("HEJ: ", answers.filter(multiple_choice_answer=True))
# survey = Survey.objects.get(id=1)
# results = SurveyUserResult.objects.filter(published_survey=survey, id=1)
# print("Survey Results:", results)

# enps_question = Question.objects.filter(question_type="enps").first()
# answers = Answer.objects.filter(
#    survey__in=results, question=enps_question, is_answered=True
# )
# print("ENPS Answers Count:", answers.count())
