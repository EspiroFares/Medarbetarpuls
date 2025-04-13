from medarbetarapp.models import *

# exec(open('medarbetarapp/view_db.py').read())
# Count total objects
print("Answers:", Answer.objects.count())
print("Questions:", Question.objects.count())
print("Surveys:", Survey.objects.count())
print("SurveyResults:", SurveyResult.objects.count())
print("\n")
# View some actual entries
# print("\nSome Answers:")
# for a in Answer.objects.all()[:5]:
#    print(a.free_text_answer, a.is_answered)

# print("\nSome Questions:")
# for q in Question.objects.all()[:5]:
#   print(q.question, q.question_format)

print("\nMultiple Choice Questions and Their Options:\n")
for q in Question.objects.filter(question_format=QuestionFormat.MULTIPLE_CHOICE):
    print("HEJ:", q.specific_question)
    if q.specific_question:
        print(f"Question: {q.question}")
        print(f"Options: {q.specific_question.options}")
        print("-" * 40)

for u in CustomUser.objects.all():
    print(f"Name: {u.name}")
print("-" * 40)
for s in Survey.objects.all():
    print(f"Survey ID: {s.id}, Name: {s.name}")
print("-" * 40)

print(type(SurveyResult.objects.filter(published_survey=Survey.objects.first())))
# for s in SurveyResult.objects.all():
#   print(f"Survey Result ID: {s.id}")
# print("\n")
answers = Answer.objects.all()
for a in Answer.objects.all():
    print(f"Answer: {a.multiple_choice_answer}")

print("HEJ: ", answers.filter(multiple_choice_answer=True))
# survey = Survey.objects.get(id=1)
# results = SurveyResult.objects.filter(published_survey=survey, id=1)
# print("Survey Results:", results)

# enps_question = Question.objects.filter(question_type="enps").first()
# answers = Answer.objects.filter(
#    survey__in=results, question=enps_question, is_answered=True
# )
# print("ENPS Answers Count:", answers.count())
