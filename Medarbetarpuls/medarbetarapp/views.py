from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


def index(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")


def chart_view(request):
    # Dummy test data
    labels = ["Happy", "Neutral", "Unhappy"]
    data = [10, 5, 2]

    context = {
        "labels": labels,
        "data": data,
    }
    return render(request, "index.html", context)
