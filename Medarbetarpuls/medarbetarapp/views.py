from django.shortcuts import render
import logging
from collections import Counter
from .models import Answer, AnalysisHandler, Question, Survey, SurveyResult

logger = logging.getLogger(__name__)


def index(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")


def chart_view1(request):
    # Get only answered answers with a non-empty free_text_answer
    answers = Answer.objects.filter(
        is_answered=True, free_text_answer__isnull=False
    ).exclude(free_text_answer="")

    # Count the frequency of each unique answer
    texts = [answer.free_text_answer for answer in answers]
    frequency = Counter(texts)

    # Prepare labels and data for Chart.js
    labels = list(frequency.keys())
    print(labels)
    data = list(frequency.values())
    print(data)
    context = {
        "labels": labels,
        "data": data,
    }

    return render(request, "index.html", context)


def chart_view(request):
    SURVEY_ID = 1  # Choose what survey you want to show here

    survey = Survey.objects.get(id=SURVEY_ID)
    results = SurveyResult.objects.filter(published_survey=survey, id=SURVEY_ID)
    # ---- ENPS SCORES ----
    enps_question = Question.objects.filter(question_type="enps").first()

    # this line gets ALL answers from this survey (over time)
    enps_all_answers = Answer.objects.filter(
        is_answered=True,
        question=enps_question,
        slider_answer__isnull=False,
        survey__published_survey__id=SURVEY_ID,
    )

    # this line gets answers from one specific survey
    enps_answers = Answer.objects.filter(
        survey__in=results, question=enps_question, is_answered=True
    )

    promoters = enps_answers.filter(slider_answer__gte=9).count()
    passives = enps_answers.filter(slider_answer__gte=7, slider_answer__lt=9).count()
    detractors = enps_answers.filter(slider_answer__lt=7).count()

    enps_labels = ["Promoters", "Passives", "Detractors"]
    enps_data = [promoters, passives, detractors]
    # analysisHandler = AnalysisHandler()
    # print(analysisHandler.calcENPS(promoters, passives, detractors))
    context = {
        "enps_labels": enps_labels,
        "enps_data": enps_data,
    }

    return render(request, "index.html", context)


def chart_view_test(request):
    # If no real data exists, show sample data
    labels = ["Happy", "Neutral", "Sad"]
    data = [3, 2, 1]

    context = {
        "labels": labels,
        "data": data,
    }

    return render(request, "index.html", context)
