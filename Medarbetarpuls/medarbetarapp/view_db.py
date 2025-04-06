from medarbetarapp.models import Answer, Question, SurveyResult

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

print("\nSome SurveyResults:")
for r in SurveyResult.objects.all()[:5]:
    print(r.id, r.user_id)
