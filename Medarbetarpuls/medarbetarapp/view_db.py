from medarbetarapp.models import Answer, Question, SurveyResult, Survey

# Count total objects
print("Answers:", Answer.objects.count())
print("Questions:", Question.objects.count())
print("SurveyResults:", SurveyResult.objects.count())

# View some actual entries
print("\nSome Answers:")
for a in Answer.objects.all()[:5]:
    print(a.free_text_answer, a.is_answered)

print("\nSome Questions:")
for q in Question.objects.all()[:5]:
    print(q.question, q.question_format)


for s in Survey.objects.all():
    print(f"Survey ID: {s.id}, Name: {s.name}")
survey = Survey.objects.get(id=1)
results = SurveyResult.objects.filter(published_survey=survey, id=1)
print("Survey Results:", results)

enps_question = Question.objects.filter(question_type="enps").first()
answers = Answer.objects.filter(
    survey__in=results, question=enps_question, is_answered=True
)
print("ENPS Answers Count:", answers.count())
