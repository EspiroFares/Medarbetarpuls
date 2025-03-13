from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


def index(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")
