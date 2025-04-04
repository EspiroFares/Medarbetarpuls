import logging
from . import models
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth import authenticate, login

logger = logging.getLogger(__name__)


def index_view(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")

def create_acc_redirect(request):
    if request.headers.get("HX-Request"):
        return HttpResponse(headers={"HX-Redirect": "/create_acc_view/"})  # Redirects in HTMX

    return redirect("/create_acc_view/")  # Normal Django redirect for non-HTMX requests

def create_acc_view(request):
    return render(request, "create_acc.html")  # Normal Django redirect for non-HTMX requests

@csrf_protect
def create_acc(request) -> HttpResponse:
    """
    Creates an account with the fetched input 
    if the email is in the organization email list

    Args:
        request: The input text from the name, email and password fields 

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400  
    """
    if request.method == 'POST':
        if request.headers.get('HX-Request'):
            name = request.POST.get('name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            # Check that email is registrated to org
            if not models.EmailList.objects.filter(email=email).exists():
                logger.error("This email is not authorized for registration.")
                return HttpResponse(status=400) 
            
            models.CustomUser.objects.create_user(email,name,password)
            return render(request, "partials/create_form.html")
    
    return HttpResponse(status=400)  # Bad request if no expression

def add_employee_view(request):
    return render(request, 'add_employee.html')

@csrf_exempt
def add_employee_email(request) -> HttpResponse:
    """
    Adds the given email to the organization
    email list of allowed emails. An email in 
    this list is required to create an account. 

    Args:
        request: The input text from the email field 

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400  
    """
    if request.method == 'POST':
        if request.headers.get('HX-Request'):
            email = request.POST.get('email')
            email_instance = models.EmailList(email=email)
            email_instance.save()
            return HttpResponse(status=204)
    
    return HttpResponse(status=400)  # Bad request if no expression

def analysis_view(request):
    return render(request, 'analysis.html')

def answer_survey_view(request):
    return render(request, 'answer_survey.html')

def authentication_acc_view(request):
    return render(request, 'authentication_acc.html')

def authentication_org_view(request):
    return render(request, 'authentication_org.html')

def create_org_view(request):
    return render(request, 'create_org.html')

def create_survey_view(request):
    return render(request, 'create_survey.html')

def login_view(request):

    #maybe implement sesion timer so you dont get logged out??
    if request.user.is_authenticated:
        logger.debug("User %e is already logged in.", request.user)
        #return redirect('start_user')
     
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            logger.debug("User %e has role: %e", email, user.user_role)
            if user.is_active:
                login(request, user)
                if user.user_role == models.UserRole.ADMIN:
                    logger.debug("Admin %e successfully logged in.", email)
                    return redirect('start_admin')
                else:  #implement check if user is creator or responder?
                    logger.debug("User %e successfully logged in.", email)
                    return redirect('start_user')
            else:
                logger.warning("Login attempt for inactive user %e", email)
                return render(request, 'login.html')
        else:
            logger.warning("Failed login attempt for %e", email)
            return render(request, 'login.html')

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

