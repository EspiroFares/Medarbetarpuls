from django.shortcuts import render
import logging
from collections import Counter
from .models import Answer

logger = logging.getLogger(__name__)


def index(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")


def chart_view(request):
    # Get only answered answers with a non-empty free_text_answer
    answers = Answer.objects.filter(is_answered=True).exclude(free_text_answer="")

    # Count the frequency of each unique answer
    texts = [answer.free_text_answer for answer in answers]
    frequency = Counter(texts)

    # Prepare labels and data for Chart.js
    labels = list(frequency.keys())
    data = list(frequency.values())

    context = {
        "labels": labels,
        "data": data,
    }

    return render(request, "index.html", context)
