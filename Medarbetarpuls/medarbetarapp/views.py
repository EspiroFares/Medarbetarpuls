from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


def index_view(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")

def add_employee_view(request):
    return render(request, 'add_employee.html')

def analysis_view(request):
    return render(request, 'analysis.html')

def answer_survey_view(request):
    return render(request, 'answer_survey.html')

def authentication_acc_view(request):
    return render(request, 'authentication_acc.html')

def authentication_org_view(request):
    return render(request, 'authentication_org.html')

def create_acc_view(request):
    return render(request, 'create_acc.html')

def create_org_view(request):
    return render(request, 'create_org.html')

def create_survey_view(request):
    return render(request, 'create_survey.html')

def login_view(request):
    return render(request, 'login.html')

def my_org_view(request):
    return render(request, 'my_org.html')

def my_results_view(request):
    return render(request, 'my_results.html')

def my_surveys_view(request):
    return render(request, 'my_surveys.html')

def publish_survey_view(request):
    return render(request, 'publish_survey.html')

def settings_admin_view(request):
    return render(request, 'settings_admin.html')

def settings_user_view(request):
    return render(request, 'settings_user.html')

def start_admin_view(request):
    return render(request, 'start_admin.html')

def start_user_view(request):
    return render(request, 'start_user.html')

def survey_result_view(request):
    return render(request, 'survey_result.html')

def survey_status_view(request):
    return render(request, 'survey_status.html')

def unanswered_surveys_view(request):
    return render(request, 'unanswered_surveys.html')

