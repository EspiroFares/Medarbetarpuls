from . import models
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from django.utils import timezone
from .models import SurveyResult

import logging

logger = logging.getLogger(__name__)


def index_view(request):
    logger.info("Testing")
    logger.warning("Testing warning!")
    logger.error("Testing error!!!")

    return render(request, "index.html")


def create_acc_redirect(request):
    if request.headers.get("HX-Request"):
        return HttpResponse(
            headers={"HX-Redirect": "/create_acc_view/"}
        )  # Redirects in HTMX

    return redirect("/create_acc_view/")  # Normal Django redirect for non-HTMX requests


def create_acc_view(request):
    return render(
        request, "create_acc.html"
    )  # Normal Django redirect for non-HTMX requests


@csrf_protect
def create_acc(request) -> HttpResponse:
    """
    Creates an account with the fetched input, if the
    email exists in any organization email list, to said
    organization.

    Args:
        request: The input text from the name, email and password fields

    Returns:
        HttpResponse: Redirects to login page if all is good, otherwise error message 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")

            # Check that email is registrated to an org
            org = find_organization_by_email(email)
            if org is None:
                logger.error("This email is not authorized for registration.")
                return HttpResponse(status=400)

            # Create user
            new_user = models.CustomUser.objects.create_user(email, name, password)

            # Add new user to base (everyone) employee group of org
            base_group = org.employee_groups.filter(name="Alla").first()  # pyright: ignore

            if base_group:
                new_user.employee_groups.add(base_group)
                new_user.save()
            else:
                logger.error(
                    f"No group found with the name '{base_group}' in the organization '{org.name}'"
                )
                return HttpResponse(status=400)

            return HttpResponse(headers={"HX-Redirect": "/"})  # Redirect to login page

    return HttpResponse(status=400)  # Bad request if no expression


def find_organization_by_email(email: str) -> models.Organization | None:
    email_entry = get_object_or_404(models.EmailList, email=email)
    return email_entry.org  # Follow the ForeignKey to Organization


def add_employee_view(request):
    return render(request, "add_employee.html", {"organization": request.user.admin})


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
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            email = request.POST.get("email")
            user = request.user

            if user.user_role == models.UserRole.ADMIN and hasattr(user, "admin"):
                org = user.admin
                email_instance = models.EmailList(email=email, org=org)
                email_instance.save()
                return HttpResponse(status=204)

    return HttpResponse(status=400)  # Bad request if no expression


def analysis_view(request):
    return render(request, "analysis.html")


def answer_survey_view(request):
    return render(request, "answer_survey.html")


def authentication_acc_view(request):
    return render(request, "authentication_acc.html")


def authentication_org_view(request):
    return render(request, "authentication_org.html")


def create_org_view(request):
    return render(request, "create_org.html")


def create_org_redirect(request):
    if request.headers.get("HX-Request"):
        return HttpResponse(
            headers={"HX-Redirect": "/create_org_view/"}
        )  # Redirects in HTMX

    return redirect("/create_org_view/")  # Normal Django redirect for non-HTMX requests


@csrf_protect
def create_org(request) -> HttpResponse:
    """
    Creates an organization and admin account
    with the fetched input

    Args:
        request: The input text from the org_name, name, email and password fields

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            org_name = request.POST.get("org_name")
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")

            # Create organization
            org = models.Organization(name=org_name)
            org.save()

            # Create admin account
            admin_account = models.CustomUser.objects.create_user(email, name, password)
            admin_account.user_role = models.UserRole.ADMIN
            admin_account.is_staff = True
            admin_account.is_superuser = True

            # Link admin account to org
            admin_account.admin = org
            admin_account.save()

            # Create base (everyone) employee group
            base_group = models.EmployeeGroup(name="Alla", organization=org)
            base_group.save()

            # Adding a org approved email for easy testing
            test_email = models.EmailList(email="user22@example.com", org=org)
            test_email.save()

            return HttpResponse(headers={"HX-Redirect": "/"})  # Redirect to login page

    return HttpResponse(status=400)  # Bad request if no expression


def create_org_redirect(request):
    if request.headers.get("HX-Request"):
        return HttpResponse(headers={"HX-Redirect": "/create_org_view/"})  # Redirects in HTMX

    return redirect("/create_org_view/")  # Normal Django redirect for non-HTMX requests

@csrf_protect
def create_org(request) -> HttpResponse:
    """
    Creates an organization and admin account  
    with the fetched input  

    Args:
        request: The input text from the org_name, name, email and password fields 

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400  
    """
    if request.method == 'POST':
        if request.headers.get('HX-Request'):
            org_name = request.POST.get('org_name')
            name = request.POST.get('name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            # Create organization
            org = models.Organization(name=org_name)
            org.save()

            # Create admin account
            admin_account = models.CustomUser.objects.create_user(email,name,password)
            admin_account.user_role = models.UserRole.ADMIN
            admin_account.is_staff = True
            admin_account.is_superuser = True

            # Link admin account to org
            admin_account.admin = org
            admin_account.save()

            # Create base (everyone) employee group
            base_group = models.EmployeeGroup(name="Alla", organization=org)
            base_group.save()

            # Adding a org approved email for easy testing
            test_email = models.EmailList(email="user22@example.com", org=org)
            test_email.save()
            
            return HttpResponse(headers={"HX-Redirect": "/"})  # Redirect to login page 
    
    return HttpResponse(status=400)  # Bad request if no expression

def create_survey_view(request):
    return render(request, "create_survey.html")


def login_view(request):
    # maybe implement sesion timer so you dont get logged out??
    if request.user.is_authenticated:
        logger.debug("User %e is already logged in.", request.user)
        # return redirect('start_user')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            logger.debug("User %e has role: %e", email, user.user_role)
            if user.is_active:
                login(request, user)
                if user.user_role == models.UserRole.ADMIN:
                    logger.debug("Admin %e successfully logged in.", email)
                    return redirect("start_admin")
                else:  # implement check if user is creator or responder?
                    logger.debug("User %e successfully logged in.", email)
                    return redirect("start_user")
            else:
                logger.warning("Login attempt for inactive user %e", email)
                return render(request, "login.html")
        else:
            logger.warning("Failed login attempt for %e", email)
            return render(request, "login.html")

    return render(request, "login.html")


def my_org_view(request):
    organization = request.user.admin

    # Retrieve all employee groups associated with this organization
    employee_groups = models.EmployeeGroup.objects.filter(organization=organization)

    # Collect all employees from these groups
    employees = models.CustomUser.objects.filter(
        employee_groups__in=employee_groups
    ).distinct()
    return render(
        request,
        "my_org.html",
        {
            "user": request.user,
            "organization": organization,
            "employees": employees,
        },
    )
    # TODO: test if this works, must be logged in


def my_results_view(request):
    user = request.user  # Assuming the user is authenticated
    answered_count = user.count_answered_surveys()
    answered_surveys = user.get_answered_surveys()

    # Assuming survey deadline is converted to UTC-timezone
    current_time = timezone.now()

    return render(request, "my_results.html" , {
        'answered_count': answered_count,
        'answered_surveys': answered_surveys,
        'current_time': current_time,
    })


def my_surveys_view(request):
    return render(request, "my_surveys.html")


def publish_survey_view(request):
    return render(request, "publish_survey.html")


def settings_admin_view(request):
    return render(
        request,
        "settings_admin.html",
        {"user": request.user, "organization": request.user.admin},
    )


def settings_user_view(request):
    return render(request, "settings_user.html", {"user": request.user})


def start_admin_view(request):
    return render(
        request, "start_admin.html"
    )  # Fix so only works if the user is actually an admin


def start_user_view(request):
    return render(request, "start_user.html")


def survey_result_view(request, survey_id):

    survey_result = get_object_or_404(SurveyResult, id=survey_id)

    # Check if the survey is accessible to the user
    if not survey_result.survey.accessible_users.filter(id=request.user.id).exists():
        return render(request, '403.html', status=403)  # Custom 403 page

    # Proceed to render the survey results
    return render(request, 'survey_result.html', {'survey_result': survey_result})

def survey_status_view(request):
    return render(request, "survey_status.html")


def unanswered_surveys_view(request):
    user = request.user  # Assuming the user is authenticated
    unanswered_count = user.count_unanswered_surveys()
    unanswered_surveys = user.get_unanswered_surveys()
    return render(request, "unanswered_surveys.html", {
        'unanswered_count': unanswered_count,
        'unanswered_surveys': unanswered_surveys,
    })
