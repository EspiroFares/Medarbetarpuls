from . import models
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
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

            existing_user = models.CustomUser.objects.filter(email=email).first()
            if existing_user:
                # Should they be able to reset name and password???
                existing_user.name = name
                existing_user.set_password(password)
                existing_user.save()
                return HttpResponse(headers={"HX-Redirect": "/"})
                # check for basegroup??
            else:
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

                return HttpResponse(
                    headers={"HX-Redirect": "/"}
                )  # Redirect to login page

    return HttpResponse(status=400)  # Bad request if no expression


def find_organization_by_email(email: str) -> models.Organization | None:
    email_entry = get_object_or_404(models.EmailList, email=email)
    return email_entry.org  # Follow the ForeignKey to Organization


@login_required
@csrf_exempt
def add_employee_view(request):
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
        email = request.POST.get("email")
        user = request.user

        if user.user_role == models.UserRole.ADMIN and hasattr(user, "admin"):
            org = user.admin

            existing_user = models.CustomUser.objects.filter(email=email).first()
            if existing_user:
                if not existing_user.is_active:
                    existing_user.is_active = True
                    existing_user.save()
                else:
                    logger.error("Existing user already have an active account")
                    pass
                    # Vad gör vi med folk som vill bli registerade till 2 organisationer

            else:
                email_instance = models.EmailList(email=email, org=org)
                email_instance.save()
            return HttpResponse(status=204)  # maybe should render back to my_org?

    return render(
        request,
        "add_employee.html",
        {"pagetitle": f"Lägg till medarbetare i<br>{request.user.admin.name}"},
    )


@login_required
def analysis_view(request):
    return render(request, "analysis.html")


@login_required
def answer_survey_view(request):
    return render(request, "answer_survey.html")


def authentication_acc_view(request):
    return render(request, "authentication_acc.html")


def authentication_org_view(request):
    return render(request, "authentication_org.html")


def create_org_view(request):
    return render(request, "create_org.html")


def create_question(request):
    return render(request, "create_question.html")


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


def create_survey_view(request):
    return render(request, "create_survey.html")


def edit_question_view(request):
    return render(request, "edit_question.html")


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


@csrf_protect
@login_required
def my_org_view(request):
    organization = request.user.admin

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        if request.user.user_role == models.UserRole.ADMIN:
            employee_to_remove = models.CustomUser.objects.get(pk=user_id)
            print("removing ", employee_to_remove)
            employee_to_remove.is_active = False
            employee_to_remove.save()
        return redirect("my_org")
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
            "employees": employees,
            "pagetitle": f"Din organisation<br>{organization.name}",
        },
    )


@login_required
def my_results_view(request):
    user = request.user  # Assuming the user is authenticated
    answered_count = user.count_answered_surveys()
    answered_surveys = user.get_answered_surveys()

    # Assuming survey deadline is converted to UTC-timezone
    current_time = timezone.now()

    return render(
        request,
        "my_results.html",
        {
            "answered_count": answered_count,
            "answered_surveys": answered_surveys,
            "current_time": current_time,
            "pagetitle": "Resultat på besvarade enkäter",
        },
    )


@login_required
def my_surveys_view(request):
    return render(request, "my_surveys.html")


def settings_admin_view(request):
    # if pressed leave over account
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            newAdminEmail = request.POST.get("email")
            user = request.user
            org = user.admin

            if models.EmailList.objects.filter(email=newAdminEmail).exists():
                print("HAALLÅÅ")
                logger.error("Testing error!!!")

                user.is_active = False
                user.is_superuser = False
                user.admin = None
                user.user_role = models.UserRole.SURVEY_RESPONDER
                user.save()
                newAdmin = models.CustomUser.objects.get(email=newAdminEmail)
                newAdmin.is_superuser = True
                newAdmin.user_role = models.UserRole.ADMIN
                newAdmin.admin = org
                newAdmin.save()
                logout(request)
                return HttpResponse(headers={"HX-Redirect": "/"})
            else:
                # maybe return message so user knows it was wrong password
                pass

    return render(
        request,
        "settings_admin.html",
        {
            "user": request.user,
            "organization": request.user.admin,
            "pagetitle": "Inställningar",
        },
    )


@login_required
@csrf_protect
def settings_user_view(request):
    # FIX - needs to fix so when wrong password is written the popup doesnt dissappear and a message is sent

    # if pressed delete user
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            password = request.POST.get("password")
            email = request.user.email

            user = authenticate(request, username=email, password=password)
            if user is not None:
                user.is_active = False
                user.save()

                # user.delete() maybe not right because we want the users answers to be saved still
                logout(request)
                return HttpResponse(headers={"HX-Redirect": "/"})
            else:
                # maybe return message so user knows it was wrong password
                pass
    return render(
        request,
        "settings_user.html",
        {"user": request.user, "pagetitle": "Inställningar"},
    )


@login_required
def start_admin_view(request):
    return render(
        request, "start_admin.html", {"pagetitle": f"Välkommen<br>{request.user.name}"}
    )  # Fix so only works if the user is actually an admin


@login_required
@csrf_protect
def settings_change_name(request):
    """
    Changes the name of a CustomUser

    Args:
        request: The input text with the new name

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400
    """

    # TODO: test user input
    if request.headers.get("HX-Request"):
        new_name = request.POST.get("name")
        email = request.user.email
        user = models.CustomUser.objects.filter(email=email).first()
        user.name = new_name
        user.save()

    if request.user.admin:
        return render(
            request,
            "settings_admin.html",
            {
                "user": request.user,
                "organization": request.user.admin,
                "pagetitle": "Inställningar",
            },
        )
    else:
        return render(
            request,
            "settings_user.html",
            {
                "user": request.user,
                "organization": request.user.admin,
                "pagetitle": "Inställningar",
            },
        )


@login_required
@csrf_protect
def settings_change_pass(request):
    """
    Changes the password of a CustomUser

    Args:
        request: The input containing the old password as well as the new password

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400
    """

    if request.headers.get("HX-Request"):
        old_password = request.POST.get("pass_old")
        new_password = request.POST.get("pass_new")
        user = authenticate(request, username=request.user.email, password=old_password)
        if user:
            user.set_password(new_password)
            user.save()
            # Use this to keep the session alive (avoid being logged out immediately)
            update_session_auth_hash(request, user)
            print("saved new password")
        else:
            # Did not find any user with this password
            return HttpResponse(400)

    if request.user.admin:
        return render(
            request,
            "settings_admin.html",
            {
                "user": request.user,
                "organization": request.user.admin,
                "pagetitle": "Inställningar",
            },
        )
    else:
        return render(
            request,
            "settings_user.html",
            {
                "user": request.user,
                "pagetitle": "Inställningar",
            },
        )


@login_required
def start_user_view(request):
    return render(
        request, "start_user.html", {"pagetitle": f"Välkommen<br>{request.user.name}"}
    )


def survey_result_view(request, survey_id):
    survey_result = SurveyResult.objects.filter(id=survey_id).first()

    if survey_result is not None:
        # Check if the survey is accessible to the user
        if survey_result.user != request.user:
            survey_result = None

    # Proceed to render the survey results
    return render(request, "survey_result.html", {"survey_result": survey_result})


@login_required
def survey_status_view(request):
    return render(request, "survey_status.html")


@login_required
def unanswered_surveys_view(request):
    user = request.user  # Assuming the user is authenticated
    unanswered_count = user.count_unanswered_surveys()
    unanswered_surveys = user.get_unanswered_surveys()
    return render(
        request,
        "unanswered_surveys.html",
        {
            "unanswered_count": unanswered_count,
            "unanswered_surveys": unanswered_surveys,
            "pagetitle": "Obesvarade enkäter",
        },
    )


def chart_view1(request):
    SURVEY_ID = 2  # Choose what survey you want to show here

    # ---- ENPS SCORES ----
    enps_question = Question.objects.filter(question_type="enps").first()

    enps_answers = Answer.objects.filter(
        is_answered=True,
        question=enps_question,
        slider_answer__isnull=False,
        survey__published_survey__id=SURVEY_ID,
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


def chart_view(request):
    # If no real data exists, show sample data
    labels = ["Happy", "Neutral", "Sad"]
    data = [3, 2, 1]

    context = {
        "labels": labels,
        "data": data,
    }

    return render(request, "analysis.html", context)
