import random
import logging
import platform
from . import models
from django.db.models import Q, Max, Count
from django.utils import timezone
from django.urls import reverse
from xmlrpc.client import Boolean
from django.core.cache import cache
from datetime import datetime, time
from django.http import HttpResponse
from .models import QuestionType, SurveyUserResult, EmployeeGroup, QuestionFormat
from django.core.mail import send_mail
from .tasks import schedule_notification, publish_survey_async
from django.utils.timezone import make_aware
from .analysis_handler import AnalysisHandler
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from .decorators import allowed_roles, logout_required
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, IntegerField, Value
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from .standard_questions import STANDARD_QUESTIONS


logger = logging.getLogger(__name__)


@csrf_protect
def create_acc(request):
    """
    Initiates account creation by saving user data to session, sending a verification code via email,
    and redirecting to the authentication page (supports both HTMX and standard requests).

    Args:
        request: The HTTP request containing name, email, password, and optional from_settings flag.

    Returns:
        HttpResponse: For POST, sends an HX-Redirect header or standard redirect to "/authentication-acc/";
        for GET, redirects or renders "create_acc.html"; or 400 on error.
    """

    if request.method == "POST":
        name = request.POST.get("name")
        # Get the name on a nice looking form
        correct_form_name = correct_name(name)
        if not correct_form_name:
            # Did not enter both firstname and lastname
            return HttpResponse(
                "Vänligen ange ditt namn på formen: Förnamn Efternamn", status=400
            )

        email = request.POST.get("email")
        password = request.POST.get("password")
        from_settings = request.POST.get("from_settings") == "true"

        user = models.CustomUser.objects.filter(email=email).exists()
        if user:
            active_user = models.CustomUser.objects.get(email=email)
            if active_user.is_active == True:
                # There already exists an user with this email
                return HttpResponse(
                    "Det existerar redan en användare med denna mejladress", status=400
                )

        org = find_organization_by_email(email=email)
        if not org:
            logger.error("This email is not authorized for registration.")
            return HttpResponse(
                "Denna mejladress tillhör ej någon organisation", status=400
            )

        code = 123456  # make random later, just test now
        cache.set(f"verify_code_{email}", code, timeout=300)

        send_mail(
            subject="Your Verification Code",
            message=f"Your verification code is: {code}",
            from_email="medarbetarpuls@gmail.com",
            recipient_list=[email],
            fail_silently=False,
        )

        # Save potential user account data in session
        request.session["user_data"] = {
            "name": correct_form_name,
            "password": password,
            "from_settings": from_settings,
        }
        # Save the mail where the two factor code is sent
        request.session["email_two_factor_code"] = email

        # Redirect till autentiseringssidan
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/authentication-acc/"})
        else:
            return redirect("/authentication-acc/")

    else:
        # Handles GET-request: Renders create-acc page
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/create_acc/"})
        else:
            return render(request, "create_acc.html")


@login_required
@csrf_protect
@allowed_roles("admin")
def edit_employee_group_view(request):
    """
    Adds new employee group to the given user

    Args:
        request: The input user and new employee group from the field

    Returns:
        HttpResponse: Returns status 200 if all is good, otherwise 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            email = request.POST.get("add-employee-group-email")
            employee_group = request.POST.get("new_employee_group")
            user = request.user
            org = user.admin
            edit_user = models.CustomUser.objects.get(email=email)
            if models.EmployeeGroup.objects.filter(name=employee_group).exists():
                group = models.EmployeeGroup.objects.get(name=employee_group)
            else:
                # create new employee group and tell the admin that they created
                # a new one and that it will be empty
                group = models.EmployeeGroup(name=employee_group, organization=org)
                group.save()
            edit_user.employee_groups.add(group)
            edit_user.save()
            return HttpResponse(status=200)

    return HttpResponse(status=400)


@login_required
@csrf_protect
@allowed_roles("admin")
def edit_survey_group_view(request):
    """
    Adds new survey group to the given user

    Args:
        request: The input user and new survey group from the field

    Returns:
        HttpResponse: Returns status 200 if all is good, otherwise 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            email = request.POST.get("add-survey-group-email")
            survey_group = request.POST.get("new_survey_group")
            user = request.user
            org = user.admin
            edit_user = models.CustomUser.objects.get(email=email)
            if models.EmployeeGroup.objects.filter(name=survey_group).exists():
                group = models.EmployeeGroup.objects.get(name=survey_group)
            else:
                # create new employee group and tell the admin that they created
                # a new one and that it will be empty
                group = models.EmployeeGroup(name=survey_group, organization=org)
                group.save()
            edit_user.survey_groups.add(group)
            edit_user.save()
            return HttpResponse(status=200)

    return HttpResponse(status=400)


@login_required
@csrf_protect
@allowed_roles("admin")
def edit_employee_view(request):
    """
    Edits the given users role to the new given role

    Args:
        request: The input user and role from the field

    Returns:
        HttpResponse: Returns status 200 if all is good, otherwise 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            email = request.POST.get("email")
            user_role = request.POST.get("edit_user_role")
            edit_user = models.CustomUser.objects.get(email=email)
            edit_user.user_role = user_role
            edit_user.save()
            return HttpResponse(status=200)

    return HttpResponse(status=400)


@login_required
@csrf_protect
@allowed_roles("admin")
def add_employee_view(request):
    """
    Adds the given email to the organization
    email list of allowed emails. An email in
    this list is required to create an account.

    Args:
        request: The input text from the authentication code field

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400
    """

    if request.method == "POST":
        email = request.POST.get("email")
        team = request.POST.get("team")
        user = request.user
        editGroup = request.POST.get("edit_employee")
        editName = request.POST.get("new_employee_group")
        editUserMail = request.POST.get("employee")
        if editGroup == "true":
            if models.EmailList.objects.filter(email=editUserMail).exists():
                org = user.admin
                if models.EmployeeGroup.objects.filter(name=editName).exists():
                    group = models.EmployeeGroup.objects.get(name=editName)
                else:
                    # create new employee group
                    group = models.EmployeeGroup(name=editName, organization=org)
                    group.save()
                editUser = models.CustomUser.objects.get(email=editUserMail)
                editUser.employee_groups.add(group)
                user.survey_groups.add(group)
                return HttpResponse("Successful", status=200)

            else:
                logger.warning("User does not exist")
                return HttpResponse("Användaren finns inte", status=400)
        elif user.user_role == models.UserRole.ADMIN and hasattr(user, "admin"):
            org = user.admin
            existing_user = models.CustomUser.objects.filter(email=email).first()
            if existing_user:
                if not existing_user.is_active:
                    if models.EmployeeGroup.objects.filter(name=team).exists():
                        group = models.EmployeeGroup.objects.filter(name=team).first()
                    else:
                        # create new employee group
                        group = models.EmployeeGroup(name=team, organization=org)
                        group.save()
                    email_instance = models.EmailList(email=email, org=org)
                    email_instance.save()
                    email_instance.employee_groups.add(group)
                    # user.survey_groups.add(group) should not be used anymore
                else:
                    logger.error("Existing user already have an active account")
                    pass
                    # Vad gör vi med folk som vill bli registerade till 2 organisationer

            else:
                if models.EmployeeGroup.objects.filter(name=team).exists():
                    group = models.EmployeeGroup.objects.filter(name=team).first()
                else:
                    # create new employee group
                    group = models.EmployeeGroup(name=team, organization=org)
                    group.save()
                email_instance = models.EmailList(email=email, org=org)
                email_instance.save()
                email_instance.employee_groups.add(group)
                # user.survey_groups.add(group) should not be used anymore
            return HttpResponse(status=204)

    return render(
        request,
        "add_employee.html",
        {"pagetitle": f"Lägg till medarbetare i<br>{request.user.admin.name}"},
    )


@login_required
@csrf_protect
@allowed_roles("surveycreator", "surveyresponder")
def answer_survey_view(
    request, survey_result_id: int, question_index: int = 0
) -> HttpResponse:
    """
    Makes it possible for the user to answer all questions of a survey.
    Page is navigated using its question index which is then used to
    save and display a unique Answer object for each Question.

    Args:
        request: The input from the various answer fields
        survey_result_id (int): The id of the SurveyResult being answered
        question_index (int): The index of the question which should be displayed

    Returns:
        HttpResponse: Redirects to next or previous question, then unanswered surveys
        page after survey completion, otherwise status 400 on errors
    """
    user: models.CustomUser = request.user
    survey_result: models.SurveyUserResult = get_object_or_404(
        SurveyUserResult, pk=survey_result_id, user=user
    )
    questions: list[models.Question] = survey_result.published_survey.questions.all()
    answers: list[models.Answer] = survey_result.answers.all()
    answer: models.Answer = models.Answer()
    survey_result = get_object_or_404(
        SurveyUserResult, pk=survey_result_id, user=request.user
    )
    questions = survey_result.published_survey.questions.all()

    # Calculate question navigation indexes
    if question_index - 1 < 0:
        prev_question_index: int = 0
    else:
        prev_question_index: int = question_index - 1

    if question_index + 1 >= len(questions):
        next_question_index: int = len(questions) - 1
    else:
        next_question_index: int = question_index + 1

    question: models.Question = questions[question_index]

    # Create a new answer if none exists for this question
    if question_index >= len(answers):
        question_format: models.QuestionFormat = question.question_format
        if question_format is not None:
            if question_format == models.QuestionFormat.SLIDER:
                answer = models.Answer(
                    survey=survey_result, question=question, slider_answer=5.0
                )
            elif question_format == models.QuestionFormat.TEXT:
                answer = models.Answer(survey=survey_result, question=question)
            elif question_format == models.QuestionFormat.YES_NO:
                answer = models.Answer(survey=survey_result, question=question)
            elif question_format == models.QuestionFormat.MULTIPLE_CHOICE:
                answer = models.Answer(survey=survey_result, question=question)
            else:
                return HttpResponse(status=400)

            answer.save()
    # Otherwise get the existing question
    else:
        answer = answers[question_index]

    if request.method == "POST":
        if request.headers.get("HX-Request"):
            question_format: models.QuestionFormat = request.POST.get("question_format")
            submit_answers: str = request.POST.get("submit_answers")
            action = request.POST.get("action_type")

            # Save the format specific answer
            if question_format is not None:
                if question_format == "slider":
                    answer.slider_answer = request.POST.get("slider")
                elif question_format == "text":
                    answer.free_text_answer = request.POST.get("text")
                elif question_format == "yesno":
                    answer.yes_no_answer = request.POST.get("yesno")
                elif question_format == "multiplechoice":
                    selected: list[str] = request.POST.getlist("multiplechoice")
                    all_options: list[str] = question.multiple_choice_question.options
                    bool_list: list[bool] = [opt in selected for opt in all_options]
                    answer.multiple_choice_answer = bool_list

                # Also save the potential comment
                answer.comment = request.POST.get("comment")
                answer.is_answered = True
                answer.save()

                # All questions answered, submit answers and redirect
                if submit_answers == "submit":
                    survey_result.is_answered = True
                    survey_result.published_survey.collected_answer_count += 1
                    survey_result.published_survey.save()
                    survey_result.save()

                    # Redirect to unanswered surveys page after completion
                    return HttpResponse(headers={"HX-Redirect": "/unanswered-surveys/"})

                if action == "previous":
                    # Redirect to previous question
                    return HttpResponse(
                        headers={
                            "HX-Redirect": "/survey/"
                            + str(survey_result.id)
                            + "/question/"
                            + str(prev_question_index)
                        }
                    )
                elif action == "next":
                    # Redirect to next question
                    return HttpResponse(
                        headers={
                            "HX-Redirect": "/survey/"
                            + str(survey_result.id)
                            + "/question/"
                            + str(next_question_index)
                        }
                    )
                elif action == "exit":
                     # Redirect back to all unanswered surveys
                     return HttpResponse(
                        headers={
                            "HX-Redirect": "/unanswered-surveys/"
                        }
                    )

            return HttpResponse(status=400)

    # This is added so a "double" loop can be used to go through
    # which boxes should be checked
    if question.multiple_choice_question is not None:
        # Edge case where no answer yet exists, but we still
        # want to display the options...
        if not answer.multiple_choice_answer:
            zipped = zip(
                question.multiple_choice_question.options,
                [False for _ in question.multiple_choice_question.options],
            )
        else:
            zipped = zip(
                question.multiple_choice_question.options, answer.multiple_choice_answer
            )
    else:
        zipped = None

    # Calculate amount of "answered" answers
    # Start at 1 because the last question always gets a saved answer
    # that is not counted
    total_answers: int = 1
    for ans in answers:
        if ans.is_answered:
            total_answers += 1

    # Sometimes the extra one added at the begining will cause this to
    # be bigger than amount of questions, do not wory about it :)
    if total_answers > len(questions):
        total_answers = len(questions)

    return render(
        request,
        "answer_survey.html",
        {
            "question": question,
            "question_index": question_index,
            "total": len(questions),
            "total_answers": total_answers,
            "survey_result_id": survey_result.id,
            "prev_question_index": prev_question_index,
            "next_question_index": next_question_index,
            "slider_answer": answer.slider_answer,
            "text_answer": answer.free_text_answer,
            "yes_no_answer": answer.yes_no_answer,
            "multiple_choice_pairs": zipped,
            "comment": answer.comment,
        },
    )


@csrf_protect
def resend_authentication_code_acc(request):
    """
    Sends a new two factor authentication code to the given email

    Args:
        request: The email and source from the input fields

    Returns:
        HttpResponse: Returns status=204 if all is good, otherwise error message 400
    """
    if request.method == "POST":
        source = request.POST.get("source")
        email = "not_defined"
        if source == "from_account":
            email = request.session.get("email_two_factor_code")
        elif source == "from_org":
            email = request.session.get("email_two_factor_code_org")
        if email == "not_defined":
            return HttpResponse("No email defined", status=404)
        code = 654321  # make random later, just test now
        cache.set(f"verify_code_{email}", code, timeout=300)
        # Send email with the code to the user
        send_mail(
            subject="Your Verification Code",
            message=f"Your verification code is: {code}",
            from_email="medarbetarpuls@gmail.com",
            recipient_list=[email],
            fail_silently=False,
        )
        return HttpResponse("Sent", status=204)
    return HttpResponse(status=400)


@csrf_protect
def authentication_acc_view(request):
    """
    Creates an account with the user information
    saved in django session if authentication code sent to
    the mail matches with the user input

    Args:
        request: The input text from the name, email and password fields

    Returns:
        HttpResponse: Redirects to login page if all is good, otherwise error message 400
    """
    if request.method == "POST":
        auth_code = request.POST.get("auth_code")
        email = request.session.get("email_two_factor_code")
        expected_code = cache.get(f"verify_code_{email}")

        if str(auth_code) == str(expected_code):
            data = request.session.get("user_data")
            name = data["name"]
            password = data["password"]

            # Delete everything saved in session and cache - data not needed anymore
            del request.session["user_data"]
            del request.session["email_two_factor_code"]
            cache.delete(f"verify_code_{email}")

            existing_user = models.CustomUser.objects.filter(email=email).first()
            if existing_user and existing_user.is_active == False:
                # Should they be able to reset name and password???
                org = find_organization_by_email(email)
                if org is None:
                    logger.error("This email is not authorized for registration.")
                    return HttpResponse(
                        "Denna mejladress tillhör ej någon organisation", status=400
                    )
                existing_user.is_active = True
                existing_user.name = name
                existing_user.user_role = models.UserRole.SURVEY_RESPONDER
                existing_user.set_password(password)
                existing_user.save()
                # Get the email and get the correct employeegroups
                email_from_list = models.EmailList.objects.get(email=email)
                group = email_from_list.employee_groups.all()
                # Add group to employee
                existing_user.employee_groups.add(*group)
                existing_user.save()
                return HttpResponse("Konto skapat. Nu kan du logga in.", status=200)
            else:
                # Check that email is registrated to an org
                org = find_organization_by_email(email)
                if org is None:
                    logger.error("This email is not authorized for registration.")
                    return HttpResponse(
                        "Denna mejladress tillhör ej någon organisation", status=400
                    )
                # Create user
                new_user = models.CustomUser.objects.create_user(email, name, password)
                # get the email and get the correct employeegroups
                email_from_list = models.EmailList.objects.get(email=email)
                group = email_from_list.employee_groups.all()
                # add group to employee
                new_user.employee_groups.add(*group)
                new_user.save()
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

                return HttpResponse("Konto skapat. Nu kan du logga in.", status=200)
        else:
            logger.error("Wrong authentication code")
            return HttpResponse("Felaktig kod", status=400)

    return render(request, "authentication_acc.html")


@csrf_protect
def authentication_org_view(request):
    """
    Creates an admin account and an organisation
    with the user information saved in
    django session if authentication code sent to
    the mail matches with the user input

    Args:
        request: The input text from the org_name, name, email and password fields

    Returns:
        HttpResponse: Redirects to login page if all is good, otherwise error message 400

    """

    if request.method == "POST":
        auth_code = request.POST.get("auth_code")
        email = request.session.get("email_two_factor_code_org")
        expected_code = cache.get(f"verify_code_{email}")
        if str(auth_code) == str(expected_code):
            data = request.session.get("user_org_data")
            org_name = str(data["org_name"])
            name = str(data["name"])
            password = str(data["password"])

            del request.session["user_org_data"]
            del request.session["email_two_factor_code_org"]
            cache.delete(f"verify_code_{email}")

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

            # TODO: Remove this and replace with better employee group handling
            # Add the admin as manager/survey creator to base group for TESTING!!!
            base_group.managers.add(admin_account)
            base_group.save()

            # Create and add standard questions to the question bank
            for question_data in STANDARD_QUESTIONS:
                question_format = question_data[2]
                options = (
                    question_data[4] if len(question_data) > 4 else None
                )  # Check if options are provided

                question: models.Question = models.Question()

                question.question_title = question_data[0]
                question.question = question_data[1]
                question.bank_question = org
                question.question_format = question_format
                question.question_type = question_data[3]

                if question_format == models.QuestionFormat.MULTIPLE_CHOICE and options:
                    multiple_choice_question = models.MultipleChoiceQuestion(
                        question_format=question_format,
                        options=question_data[4],
                    )
                    question.multiple_choice_question = multiple_choice_question
                    question.multiple_choice_question.save()
                    question.save()

                elif question_format == models.QuestionFormat.SLIDER and options:
                    slider_question = models.SliderQuestion(
                        question_format=question_format,
                        min_interval=0,
                        max_interval=10,
                        min_text="Test",
                        max_text="Test2",
                    )
                    question.slider_question = slider_question
                    question.slider_question.save()
                    question.save()

                question.save()
            return HttpResponse("Kontot skapat. Nu kan du logga in.", status=200)
        else:
            logger.error("Wrong authentication code")
            return HttpResponse("Felaktig kod", status=400)

    return render(request, "authentication_org.html")


@login_required
@allowed_roles("surveycreator", "admin")
def create_question(request, survey_id: int | None = None) -> HttpResponse:
    """
    Makes it possible to create a question with predefined formats.
    This function is reachable from create_survey.

    Agrs:
        request: The input text from the question text field
        survey_id (int): The id of the opened survey
    Returns:
        HttpResponse: Returns status 404 if the survey template does not exist
    """
    user: models.CustomUser = request.user

    source = request.GET.get("source")
    # Retrieve the survey template from the database if it belongs to the user
    survey_temp: models.SurveyTemplate = user.survey_templates.filter(
        id=survey_id
    ).first()

    # SurveyCreator needs a help-function to access organization
    if user.admin is None:
        organization: models.Organization = find_organization_by_email(email=user.email)
    else:
        organization: models.Organization = user.admin
    organization_questions: models.Question = organization.question_bank.all()

    if survey_temp is None and source != "organization_templates":
        # Handle the case where the survey template does not exist
        return HttpResponse("Survey template not found", status=404)

    # The swedish translations
    QUESTION_LABEL_TRANSLATIONS = {
        "Slider": "Skala",
        "Text": "Fritext",
        "Yes No": "Ja/Nej",
        "Multiple choice": "Flerval",
    }

    source = request.GET.get("source")
    print(f"Source: {source}")

    return render(
        request,
        "create_question.html",
        {
            "survey_temp": survey_temp,
            "source": source,
            "organization_questions": organization_questions,
            "QuestionFormat": models.QuestionFormat,
            "question_labels": QUESTION_LABEL_TRANSLATIONS,
        },
    )


@csrf_protect
def create_org(request) -> HttpResponse:
    """
    Initiates organization creation by generating
    a verification code, sending it via email,
    saving form data in the session, and redirecting
    to the authentication page
    (supports HTMX and standard requests).

    Args:
        request: The HTTP request containing org_name, name, email, and password.

    Returns:
        HttpResponse: For POST, sends HX-Redirect header or standard redirect to "/authentication-org/";
        for GET, sends HX-Redirect header or renders "create_org.html". If this organization/admin account already exists, return error responese 400.
    """

    if request.method == "POST":
        # Get data from the forum
        org_name = request.POST.get("org_name")
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        correct_form_name = correct_name(name)
        if not correct_form_name:
            # Did not enter both firstname and lastname
            return HttpResponse(
                "Vänligen ange ditt namn på formen: Förnamn Efternamn", status=400
            )

        code = 123456  # make random later, just test now
        cache.set(f"verify_code_{email}", code, timeout=300)

        user = models.CustomUser.objects.filter(email=email).exists()
        if user:
            # There already exists an user with this email
            return HttpResponse(
                "Det existerar redan en användare med denna mejladress", status=400
            )

        # Send email with the code to the user
        send_mail(
            subject="Din verifieringskod",
            message=f"Din verifieringskod är: {code}",
            from_email="medarbetarpuls@gmail.com",
            recipient_list=[email],
            fail_silently=False,
        )

        # Save potential user account data in session
        request.session["user_org_data"] = {
            "org_name": org_name,
            "name": name,
            "password": password,
        }
        # Save the mail where the two factor code is sent
        request.session["email_two_factor_code_org"] = email

        # Redirect to authentication
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/authentication-org/"})
        return redirect("/authentication-org/")

    else:
        # GET-request: render or redirect to create_org
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/create_org/"})
        return render(request, "create_org.html")


@csrf_protect
@login_required
@allowed_roles("surveycreator", "admin")
def delete_question(
    request, question_id: int, survey_id: int | None = None
) -> HttpResponse:
    """
    Makes it possible to delete a specific question from
    a specific survey.

    Args:
        request: The input click from trash button
        survey_id (int): The id of the opened survey
        question_id (int): The id of the clicked question
    Returns:
        HttpResponse: Redirects to create_survey or 400
    """

    source = request.GET.get("source")
    print(f"Source: {source}")

    if request.method == "POST":
        if request.headers.get("HX-Request"):
            question: models.Question = get_object_or_404(
                models.Question, id=question_id
            )
            question.delete()

            if survey_id is None:
                # If no survey_id is given, redirect to create_survey
                hx_redirect_url = ""
            else:
                hx_redirect_url = f"/create-survey/{survey_id}"
                if source:  # Only append source if it's not None or empty
                    hx_redirect_url += f"?source={source}"

            return HttpResponse(headers={"HX-Redirect": hx_redirect_url})

    return HttpResponse(status=400)  # Bad request if no expression


@csrf_protect
@login_required
def move_question_left(request, survey_temp_id: int, question_id: int) -> HttpResponse:
    """
    Moves the selected question to the left if possible

    Args:
        survey_temp_id (int): The id of the opened survey
        question_id (int): The id of the clicked question
    Returns:
        HttpResponse: Renders a copy of the question-list
    """
    survey_temp: models.SurveyTemplate = get_object_or_404(
        models.SurveyTemplate, pk=survey_temp_id
    )
    q_order: models.QuestionOrder = get_object_or_404(
        models.QuestionOrder, survey_temp=survey_temp, question_id=question_id
    )

    # Find the immediate predecessor
    prev: models.QuestionOrder = (
        models.QuestionOrder.objects.filter(
            survey_temp=survey_temp, order__lt=q_order.order
        )
        .order_by("-order")
        .first()
    )

    if prev:
        # swap their order values
        q_order.order, prev.order = prev.order, q_order.order
        q_order.save()
        prev.save()

    source = request.GET.get("source")

    context = {
        "survey_temp": survey_temp,
        "source": source,
    }

    return render(request, "partials/question-list.html", context)


@csrf_protect
@login_required
def move_question_right(request, survey_temp_id: int, question_id: int) -> HttpResponse:
    """
    Moves the selected question to the right if possible

    Args:
        survey_temp_id (int): The id of the opened survey
        question_id (int): The id of the clicked question
    Returns:
        HttpResponse: Renders a copy of the question-list
    """
    survey_temp: models.SurveyTemplate = get_object_or_404(
        models.SurveyTemplate, pk=survey_temp_id
    )
    q_order: models.QuestionOrder = get_object_or_404(
        models.QuestionOrder, survey_temp=survey_temp, question_id=question_id
    )

    # Find the immediate successor
    nxt: models.QuestionOrder = (
        models.QuestionOrder.objects.filter(
            survey_temp=survey_temp, order__gt=q_order.order
        )
        .order_by("order")
        .first()
    )
    if nxt:
        q_order.order, nxt.order = nxt.order, q_order.order
        q_order.save()
        nxt.save()

    source = request.GET.get("source")

    context = {
        "survey_temp": survey_temp,
        "source": source,
    }

    return render(request, "partials/question-list.html", context)

@login_required
def create_survey_view(request, survey_id: int | None = None) -> HttpResponse:
    """
    Creates a survey template. If no survey_id is given, a new
    survey template is created. If the survey_id is given, the
    corresponding survey template is fetched from the database.

    Args:
        request: The input text from the question text field
        survey_id (int): The id of the opened survey

    Returns:
        HttpResponse: Redirects to create_survey or renders create_survey_view
    """
    source = request.GET.get("source")

    if survey_id is None:
        if request.method == "POST":
            raw_name = request.POST.get("name", "").strip()

            if not raw_name:
                # re-fetch lists for the “templates_and_drafts” page:
                survey_templates = request.user.survey_templates.all()
                org_templates = (
                    request.user.admin.survey_template_bank.all()
                    if source == "organization_templates" and request.user.admin
                    else None
                )
                return render(
                    request,
                    "templates_and_drafts.html",
                    {
                        "survey_templates": survey_templates,
                        "organization_survey_templates": org_templates,
                        "error": "Du måste ange ett namn på enkäten",
                    },
                )

            survey_temp = models.SurveyTemplate(
                creator=request.user,
                name=raw_name,
                last_edited=timezone.now(),
            )
            survey_temp.save()

            if source == "organization_templates" and request.user.admin:
                request.user.admin.survey_template_bank.add(survey_temp)

            redirect_url = reverse("create_survey_with_id", args=[survey_temp.id])
            if source:
                redirect_url += f"?source={source}"
            return redirect(redirect_url)

        # disallow GET without an ID
        return HttpResponseNotAllowed(["POST"])

    user = request.user
    if source == "readonly":
        org = find_organization_by_email(email=user.email)
        survey_temp = org.survey_template_bank.filter(id=survey_id).first()
    else:
        survey_temp = user.survey_templates.filter(id=survey_id).first()

    if not survey_temp:
        return HttpResponse("Survey template not found", status=404)

    # this GET simply renders the edit page—no HX-Redirect anymore
    return render(
        request,
        "create_survey.html",
        {"survey_temp": survey_temp, "source": source},
    )



@login_required
@allowed_roles("surveycreator", "admin")
def edit_question_view(
    request,
    question_format: models.QuestionFormat,
    survey_id: int | None = None,
    question_id: str | None = None,
) -> HttpResponse:
    """
    Makes it possible to edit a question. This function is reachable
    from both create_survey and create_question views.

    Args:
        request: The input text from the question text field
        survey_id (int): The id of the opened survey
        question_format (QuestionFormat): The format of the question being created/edited
        question_id (int): The id of edited/created question, None if no question has been created

    Returns:
        HttpResponse: Redirects to create_survey or renders edit_question_view
    """
    user: models.CustomUser = request.user
    options = None  # Use later to show options

    source = request.GET.get("source")
    print(f"SOURCE: {source}")

    # SurveyCreator needs a help-function to access organization
    if user.admin is None:
        organization: models.Organization = find_organization_by_email(email=user.email)
    else:
        organization: models.Organization = user.admin

    bank_question = organization.question_bank.filter(id=question_id).exists()

    if source == "readonly":
        # If the question is from the bank, get it from the bank

        survey_temp: models.SurveyTemplate = organization.survey_template_bank.filter(
            id=question_id
        ).first()

    elif survey_id is not None:
        # Get the survey from given id
        survey_temp: models.SurveyTemplate = user.survey_templates.filter(
            id=survey_id
        ).first()
        if survey_temp is None:
            # Handle the case where the survey template does not exist
            return HttpResponse("Survey template not found", status=404)

    if request.method == "POST":
        if request.headers.get("HX-Request"):
            # Special case for when a question is created

            if question_id is None:
                question: models.Question = models.Question()
                question.save()

                if (
                    source == "organization_templates"
                    and request.user.admin
                    and survey_id is None
                ):
                    # If the source is from organization templates, add the question to the survey template
                    organization.question_bank.add(question)
                    # Add the question to the survey template
                else:
                    # Figure out the current max order for this survey
                    current_max = (
                        models.QuestionOrder.objects.filter(survey_temp=survey_temp)
                        .aggregate(m=Max("order"))
                        .get("m")
                        or 0
                    )
                    # The new questions order is one higher
                    next_order = current_max + 1
                    # Use through_defaults to set the right order
                    survey_temp.questions.add(
                        question, through_defaults={"order": next_order}
                    )

            elif survey_id is not None:
                question = survey_temp.questions.filter(id=question_id).exists()
                if question:
                    question = survey_temp.questions.filter(id=question_id).first()
                else:
                    question = organization.question_bank.filter(id=question_id).exists
                    if question:
                        question = organization.question_bank.filter(
                            id=question_id
                        ).first()
                        print("Question found in bank")
                    else:
                        # Handle the case where the question does not exist
                        return HttpResponse("Question not found", status=404)
            else:
                question = organization.question_bank.filter(id=question_id).exists
                if question:
                    question = organization.question_bank.filter(id=question_id).first()
                else:
                    # Handle the case where the question does not exist
                    return HttpResponse("Question not found", status=404)

            if source != "organization_templates" or survey_id is not None:
                current_max = (
                    models.QuestionOrder.objects.filter(survey_temp=survey_temp)
                    .aggregate(m=Max("order"))
                    .get("m")
                    or 0
                )
                # The new questions order is one higher
                next_order = current_max + 1

                # Use through_defaults to set the right order
                survey_temp.questions.add(
                    question, through_defaults={"order": next_order}
                )
                # Handle the case where the question does not exist

            # Check for valid question format
            if question_format not in [
                choice.value for choice in models.QuestionFormat
            ]:
                return HttpResponse("Invalid question type", status=404)

            # Specify question format
            question.question_format = question_format
            question.save()

            question_title = request.POST.get("question_name")

            if question_title is not None:
                question.question_title = question_title
                question.save()

            # Add testcase for multiplechoice questions
            if question_format == models.QuestionFormat.MULTIPLE_CHOICE:
                options = request.POST.getlist("options")
                for option in options:
                    if not option:
                        options.remove(option)
                # This is kinda fucked and can maybe be re-written better
                question.multiple_choice_question = models.MultipleChoiceQuestion(
                    question_format=question_format
                )
                question.multiple_choice_question.save()
                question.multiple_choice_question.options.extend(options)
                question.multiple_choice_question.save()
                question.save()

            # Add question text
            question.question = request.POST.get("question")
            question.save()

            if source != "organization_templates" or survey_id is not None:
                # Update last edited date of survey
                survey_temp.last_edited = timezone.now()
                survey_temp.save()
            else:
                return HttpResponse(headers={"HX-Redirect": "/organization_templates/"})

            hx_redirect_url = f"/create-survey/{survey_id}"
            if source and source != "None":  # Only append if source is valid
                hx_redirect_url += f"?source={source}"

            return HttpResponse(headers={"HX-Redirect": hx_redirect_url})

    # Checks if there is a specific question text to be displayed
    question_text: str | None = None
    if question_id is not None:
        question_text = models.Question.objects.filter(id=question_id).first().question
        if (
            models.Question.objects.filter(id=question_id)
            .first()
            .multiple_choice_question
        ):
            options = (
                models.Question.objects.filter(id=question_id)
                .first()
                .multiple_choice_question.options
            )

    context = {
        "question_format": question_format,
        "question_id": question_id,
        "question_text": question_text,
        "options": options,
        "bank_question": bank_question,
        "source": source,
    }
    if survey_id is not None:
        context.update({"survey_id": survey_id})
        context.update({"survey_temp": survey_temp})

    return render(
        request,
        "edit_question.html",
        context,
    )


@login_required
@allowed_roles("surveycreator")
def publish_survey(request, survey_id: int) -> HttpResponse:
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            # Fetch the corresponding survey template by survey id
            # from the database and render the create_survey view
            user: models.CustomUser = request.user
            survey_temp: models.SurveyTemplate = user.survey_templates.filter(
                id=survey_id
            ).exists()

            if survey_temp:
                survey_temp = user.survey_templates.filter(id=survey_id).first()
            else:
                organization: models.Organization = find_organization_by_email(
                    email=user.email
                )
                survey_temp = organization.survey_template_bank.filter(
                    id=survey_id
                ).exists()
                if survey_temp:
                    survey_temp = organization.survey_template_bank.filter(
                        id=survey_id
                    ).first()
                else:
                    # Handle the case where the survey template does not exist
                    return HttpResponse("Survey template not found", status=404)

            if survey_temp is None:
                # Handle the case where the survey template does not exist
                return HttpResponse("Survey template not found", status=404)

            if not survey_temp.questions.first():
                # Handle the case where the survey template has no questions
                return HttpResponse("Enkäten saknar frågor", status=404)

            # Get the input information:

            # Privacy checkboxes (can have multiple selected)
            privacy_choices = request.POST.getlist(
                "privacy"
            )  # returns list like ['anonymous', 'public']
            # is_anonymous: bool = 'anonymous' in privacy_choices
            is_anonymous: bool = True
            is_public: bool = "public" in privacy_choices

            # Survey name
            survey_name: str = request.POST.get("survey-name")

            # Get the receiving employee group
            employee_group_name: str = request.POST.get("send-to")
            employee_group: models.EmployeeGroup = user.survey_groups.filter(
                name=employee_group_name
            ).first()

            # Handle the case where no employee group was found
            if employee_group is None:
                return render(
                    request,
                    "partials/error_message.html",
                    {"message": "Felaktig arbetsgrupp vald"},
                    status=400,
                )

            # Get the dates
            publish_date: str = request.POST.get("publish-date")
            end_date: str = request.POST.get("end-date")

            # This will give you the days when reminders should be sent, e.g. ['3', '7', '14']
            reminders: list[str] = request.POST.getlist("reminders[]")

            # Make the dates timezone aware to keep django from complaining
            if end_date:
                naive_deadline = datetime.combine(
                    datetime.strptime(end_date, "%Y-%m-%d").date(),
                    time(hour=23, minute=55),
                )
                deadline = make_aware(naive_deadline)  # Now it's timezone-aware
            else:
                deadline = None

            if publish_date:
                naive_sending_date = datetime.combine(
                    datetime.strptime(publish_date, "%Y-%m-%d").date(),
                    time(hour=0, minute=5),
                )
                sending_date = make_aware(naive_sending_date)
            else:
                sending_date = None

            # Add standard notifications for the last two days before deadline
            if deadline and sending_date:
                days_difference = (deadline - sending_date).days

                # Only schedule if there are days left!
                if days_difference >= 2:
                    reminders.append(str(days_difference))
                    reminders.append(str(days_difference - 1))
                elif days_difference == 1:
                    reminders.append(str(days_difference))

            # Assuming survey deadline is converted to UTC-timezone
            current_time = timezone.now()

            # Ensure dates have been set correctly
            if sending_date and deadline:
                if deadline <= sending_date:
                    return render(
                        request,
                        "partials/error_message.html",
                        {
                            "message": "Sista svarsdatum måste vara efter publiceringsdatum"
                        },
                        status=400,
                    )
                if sending_date.date() < current_time.date():
                    return render(
                        request,
                        "partials/error_message.html",
                        {"message": "Publiceringsdatum måste vara från och med idag"},
                        status=400,
                    )
            else:
                return render(
                    request,
                    "partials/error_message.html",
                    {"message": "Publiceringsdatum och sista svarsdatum måste anges"},
                    status=400,
                )

            # Create a Survey to be send to employess
            survey: models.Survey = models.Survey(
                name=survey_name,
                creator=user,
                deadline=deadline,
                sending_date=sending_date,
                last_notification=current_time,
                is_viewable=is_public,
                is_anonymous=is_anonymous,
            )
            survey.save()
            survey.employee_groups.add(employee_group)
            survey.save()

            # Copy all questions from the template to the survey
            new_questions = []
            for template_q in survey_temp.get_ordered_questions():
                # clone_for_survey creates a fresh Question instance in the DB
                new_q = template_q.clone_for_survey(survey)
                new_questions.append(new_q)

            # Link survey to its copies
            survey.questions.set(new_questions)
            survey.save()

            # Only tries scheduling if we are on linux system!
            os_type = platform.system()

            if os_type == "Linux":
                publish_survey_async.apply_async(
                    args=[survey.id], eta=survey.sending_date
                )
                schedule_notification(survey.id, reminders)
            else:
                survey.publish_survey()

            return render(
                request,
                "partials/error_message.html",
                {"message": "Enkäten har nu publicerats"},
                status=200,
            )

    return HttpResponse(status=400)


@logout_required()
def login_view(request):
    """
    Authenticates the user and logs them in.
    If credentials are valid, redirects based on user role; otherwise, re-renders the login page.

    Args:
        request: The HTTP request with user login credentials.

    Returns:
        HttpResponse: Redirects to the appropriate page on success or renders the login page on failure.
    """

    # maybe implement sesion timer so you dont get logged out??
    # if request.user.is_authenticated:
    # logger.debug("User %e is already logged in.", request.user)
    # logger.debug("User %e is already logged in.", request.user)
    # return HttpResponse("Användaren %e är redan inloggad", status=400)
    # return redirect('start_user')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            logger.debug("User %e has role: %e", email, user.user_role)
            if user.is_active:
                login(request, user)
                response = HttpResponse(status=200)
                if user.user_role == models.UserRole.ADMIN:
                    response["HX-Redirect"] = "/start-admin/"
                    logger.debug("Admin %e successfully logged in.", email)
                    return response
                elif user.user_role == models.UserRole.SURVEY_RESPONDER:
                    response["HX-Redirect"] = "/start-user/"
                    logger.debug("User %e successfully logged in.", email)
                    return response
                else:
                    response["HX-Redirect"] = "/start-creator/"
                    logger.debug("User %e successfully logged in.", email)
                    return response
            else:
                logger.warning("Login attempt for inactive user %e", email)
                return HttpResponse("Användare %e är en inaktiv användare", status=400)
        else:
            logger.warning("Failed login attempt for %e", email)
            return HttpResponse("Felaktiga inloggningsuppgifter", status=400)

    return render(request, "login.html")


@csrf_protect
@login_required
@allowed_roles("admin", "surveycreator", "surveyresponder")
def logout_view(request):
    """
    A logout function that logs out the user and clears the session

    Args:
        request: HTMX post request

    Returns:
        HttpResponse: If successful redirect to login page otherwise status 400.
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            logout(request)
            request.session.flush()  # Make sure session is cleared
            response = HttpResponse(status=200)
            response["HX-Redirect"] = "/"
            return response
    return HttpResponse(status=400)


@csrf_protect
@login_required
@allowed_roles("admin")
def my_org_view(request):
    """
    Displays the organization's employee list and processes employee removal.
    For POST, deactivates a selected employee if the current user is admin.
    Supports search and HTMX requests for table updates.

    Args:
        request: The HTTP request with employee removal or search parameters.

    Returns:
        HttpResponse: Renders the organization page or redirects after a removal.
    """
    organization = request.user.admin

    if request.method == "POST":
        user_email = request.POST.get("delete_user_email")
        if request.user.user_role == models.UserRole.ADMIN:
            employee_to_remove = models.CustomUser.objects.get(email=user_email)
            print("removing ", employee_to_remove)
            employee_to_remove.is_active = False
            employee_to_remove.save()
            employee_to_remove.survey_groups.clear()
            employee_to_remove.save()

            # Get all employee_groups for this employee
            all_groups = employee_to_remove.employee_groups.all()
            # Remove all other groups except "Alla"
            group_to_keep = models.EmployeeGroup.objects.filter(name="Alla").first()
            for group in all_groups:
                if group != group_to_keep:
                    employee_to_remove.employee_groups.remove(group)

            employee_to_remove.save()
            models.EmailList.objects.filter(email=employee_to_remove.email).delete()
        return redirect("my_org")
    # Retrieve all employee groups associated with this organization
    employee_groups = models.EmployeeGroup.objects.filter(organization=organization)

    # Collect all employees from these groups
    employees = models.CustomUser.objects.filter(
        employee_groups__in=employee_groups
    ).distinct()

    # Catch search word
    search_query = request.GET.get("search", "")
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query) | Q(email__icontains=search_query)
        )

    # Check if it is a HTMX request
    if "HX-Request" in request.headers:
        # Return only table rows
        return render(
            request,
            "my_org_table.html",
            {
                "employees": employees,
            },
        )
    else:
        return render(
            request,
            "my_org.html",
            {
                "user": request.user,
                "employees": employees,
                "pagetitle": f"Din organisation<br>{organization.name}",
                "search_query": search_query,
            },
        )


@login_required
@allowed_roles("surveycreator", "surveyresponder")
def my_results_view(request):
    """
    Displays the logged-in user's survey results.
    Retrieves the count of answered surveys, the list of surveys, and current UTC time,
    then renders the "my_results.html" template.

    Args:
        request: The HTTP request with the authenticated user.

    Returns:
        HttpResponse: Renders the survey results page.
    """

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
            "user_role": user.user_role,
        },
    )


@csrf_protect
@login_required
@allowed_roles("surveycreator", "admin")
def delete_survey_template(request, survey_id: int) -> HttpResponse:
    """
    Deletes a survey template via HTMX.
    If the request is a POST and an HTMX request, deletes the survey template for the logged-in user.

    Args:
        request: The HTTP request containing the survey deletion action.
        survey_id (int): The ID of the survey template to delete.

    Returns:
        HttpResponse: Redirects to "/templates_and_drafts/" on success or returns status 400 on failure.
    """
    source = request.GET.get("source")

    if request.method == "POST":
        if request.headers.get("HX-Request"):
            survey_temp = get_object_or_404(
                models.SurveyTemplate, id=survey_id, creator=request.user
            )
            survey_temp.delete()
            if source == "organization_templates":
                return HttpResponse(headers={"HX-Redirect": "/organization_templates/"})
            else:
                return HttpResponse(headers={"HX-Redirect": "/templates_and_drafts/"})

    return HttpResponse(status=400)


@csrf_protect
@login_required
@allowed_roles("surveycreator")
def templates_and_drafts(request, search_str: str | None = None) -> HttpResponse:
    """
    Displays the survey templates and drafts page with all created survey templates.
    Also gives functionality for searching for specific surveys via
    their name.

    Args:
        request: The input text from the search field
        search_str (str | None): The search pattern to be filtered for

    Returns:
        HttpResponse: Renders my_surveys page with survey templates list
        or redirects recursively with specific search pattern.
    """
    # Annotate and filter templates with 0 questions
    empty_templates: models.SurveyTemplate = request.user.survey_templates.annotate(
        num_questions=Count("questions")
    ).filter(num_questions=0)

    organization = find_organization_by_email(email=request.user.email)
    organization_survey_templates = organization.survey_template_bank.all()

    # Delete them
    empty_templates.delete()

    if search_str is None:
        # Order templates by last time edited
        survey_templates = request.user.survey_templates.all().order_by("-last_edited")
    else:
        # Order templates by search bar input relevance
        survey_templates = request.user.survey_templates.annotate(
            relevance=Case(
                When(name__iexact=search_str, then=Value(3)),  # exact match
                When(name__istartswith=search_str, then=Value(2)),  # startswith
                When(name__icontains=search_str, then=Value(1)),  # somewhere inside
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("-relevance", "-last_edited")

    # Post request for when search button is pressed
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            search_str_input: str = request.POST.get("search-bar")

            if search_str_input is None:
                return HttpResponse(headers={"HX-Redirect": "/templates_and_drafts/"})
            else:
                return HttpResponse(
                    headers={"HX-Redirect": "/templates_and_drafts/" + search_str_input}
                )

    return render(
        request,
        "templates_and_drafts.html",
        {
            "survey_templates": survey_templates,
            "organization_survey_templates": organization_survey_templates,
        },
    )


@csrf_protect
@login_required
@allowed_roles("admin")
def organization_templates(request, search_str: str | None = None) -> HttpResponse:
    organization = request.user.admin
    survey_templates = organization.survey_template_bank.all()
    question_templates = organization.question_bank.all()
    source = "organization_templates"

    empty_templates: models.SurveyTemplate = survey_templates.annotate(
        num_questions=Count("questions")
    ).filter(num_questions=0)

    # Delete them
    empty_templates.delete()

    return render(
        request,
        "organization_templates.html",
        {
            "survey_templates": survey_templates,
            "question_templates": question_templates,
            "source": source,
        },
    )


@login_required
def my_surveys_view(request):
    return render(request, "my_surveys.html")


@csrf_protect
@login_required
def remove_employee_from_employee_group_view(request):
    """
    Removes the given employee group from the given users employee groups

    Args:
        request: Email and employee group from input fields

    Returns:
        HttpResponse: Returns status=200 if all good otherwise status=400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            email = request.POST.get("email")
            group = request.POST.get("group")
            user = models.CustomUser.objects.get(email=email)
            group_to_remove = models.EmployeeGroup.objects.filter(name=group).first()
            user.employee_groups.remove(group_to_remove)
            return HttpResponse(status=200)
    return HttpResponse(status=400)


@csrf_protect
@login_required
def remove_employee_from_survey_group_view(request):
    """
    Removes the given survey group from the given users survey groups

    Args:
        request: Email and survey group from input fields

    Returns:
        HttpResponse: Returns status=200 if all good otherwise status=400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            email = request.POST.get("email")
            group = request.POST.get("group")
            user = models.CustomUser.objects.get(email=email)
            group_to_remove = models.EmployeeGroup.objects.filter(name=group).first()
            user.survey_groups.remove(group_to_remove)
            return HttpResponse(status=200)
    return HttpResponse(status=400)


@login_required
@allowed_roles("admin")
def settings_admin_view(request):
    """
    Transfers admin rights to a new admin user.
    On HTMX POST, validates the new admin's email, updates user roles, and logs out the current admin;
    otherwise, renders the settings page.

    Args:
        request: The HTTP request containing the admin settings update.

    Returns:
        HttpResponse: Redirects to home on success or renders the settings page.
    """
    # Leave over account to new admin function
    # if pressed leave over account
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            # get new admins mail
            new_admin_email = request.POST.get("email")
            # get old admin and the organisation
            user = request.user
            org = user.admin
            if new_admin_email == user.email:
                return HttpResponse(
                    "Du kan inte lämna över konto till dig själv", status=400
                )

            # check if new email exist and then switch roles and save
            if models.EmailList.objects.filter(email=new_admin_email).exists():
                """user.is_active = False
                user.is_superuser = False
                user.admin = None
                user.user_role = models.UserRole.SURVEY_RESPONDER
                user.save()"""
                models.EmailList.objects.filter(email=user.email).delete()
                user.delete()  # maybe not right because we want the users answers to be saved still
                new_admin = models.CustomUser.objects.get(email=new_admin_email)
                new_admin.is_superuser = True
                new_admin.is_staff = True
                new_admin.user_role = models.UserRole.ADMIN
                new_admin.admin = org

                # Retrieve all employee groups associated with this organization
                employee_groups = models.EmployeeGroup.objects.filter(organization=org)
                # Get the new admin user by email
                user = models.CustomUser.objects.get(email=new_admin_email)

                # Remove the user from the specific employee group
                user.employee_groups.remove(*employee_groups)

                # models.EmailList.objects.filter(email = newAdminEmail, org=org).delete() MAYBE should delete this from emaillist because the account is now admin
                new_admin.save()
                logout(request)
                request.session.flush()  # Make sure session is cleared

                return HttpResponse(headers={"HX-Redirect": "/"})
            else:
                logger.error(" The mail entered is not an available user ")
                return HttpResponse(
                    "Den angivna mejladressen tillhör inget konto", status=400
                )

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
@allowed_roles("surveycreator", "surveyresponder")
def settings_user_view(request):
    """
    Deletes the user account after password verification.
    deletes the account on success, and logs out the user.

    Args:
        request: The HTTP request with the password for account deletion.

    Returns:
        HttpResponse: Redirects to home on deletion or returns status 400 if authentication fails.
    """

    # FIX - needs to fix so when wrong password is written the popup doesnt dissappear and a message is sent
    # Delete user function
    # if pressed delete user
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            password = request.POST.get("password")
            email = request.user.email
            # Check so password is correct
            user = authenticate(request, username=email, password=password)
            if user is not None:
                # set user to inactive and save then logout the user
                # user.is_active = False
                # user.save()
                models.EmailList.objects.filter(email=user.email).delete()
                user.delete()  # maybe not right because we want the users answers to be saved still
                logout(request)
                request.session.flush()  # Make sure session is cleared
                return HttpResponse(headers={"HX-Redirect": "/"})
            else:
                logger.error("Wrong password entered")
                return HttpResponse(status=400)
    return render(request, "settings_user.html", {"user": request.user})


@login_required
@allowed_roles("surveycreator")
def start_creator_view(request):
    user = request.user  # Assuming the user is authenticated
    unanswered_count = user.count_unanswered_surveys()
    unanswered_surveys = user.get_unanswered_surveys()
    current_time = timezone.now()
    return render(
        request,
        "start_creator.html",
        {
            "pagetitle": f"Välkommen<br>{request.user.name}",
            "unanswered_count": unanswered_count,
            "unanswered_surveys": unanswered_surveys,
            "current_time": current_time,
        },
    )  # Fix so only works if the user is actually an admin


@login_required
@csrf_protect
@allowed_roles("admin", "surveycreator", "surveyresponder")
def settings_change_name(request):
    """
    Changes the name of a CustomUser

    Args:
        request: The input text with the new name

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400
    """

    if request.headers.get("HX-Request"):
        new_name = request.POST.get("name")
        correct_form_name = correct_name(new_name)
        if not correct_form_name:
            # Did not enter both firstname and lastname
            return HttpResponse(
                "Vänligen ange ditt namn på formen: Förnamn Efternamn", status=400
            )
        email = request.user.email
        user = models.CustomUser.objects.filter(email=email).first()
        user.name = correct_form_name
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
            status=200,
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
            status=200,
        )


@login_required
@csrf_protect
@allowed_roles("admin", "surveycreator", "surveyresponder")
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
        check_password = request.POST.get("pass_check")  # The repeated new password
        user = authenticate(request, username=request.user.email, password=old_password)
        # Check that the old password is correct and that the new password is repeated
        if user and check_password == new_password:
            user.set_password(new_password)
            user.save()
            # Use this to keep the session alive (avoid being logged out immediately)
            update_session_auth_hash(request, user)
            logger.info("saved new password")
        elif not user:
            return HttpResponse("Fel lösenord", status=400)
        else:
            # New passwords did not match
            return HttpResponse("De nya lösenorden matchar inte", status=400)

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
@allowed_roles("surveyresponder")
def start_user_view(request):
    user = request.user  # Assuming the user is authenticated
    unanswered_count = user.count_unanswered_surveys()
    unanswered_surveys = user.get_unanswered_surveys()
    current_time = timezone.now()
    return render(
        request,
        "start_user.html",
        {
            "pagetitle": f"Välkommen<br>{request.user.name}",
            "unanswered_count": unanswered_count,
            "unanswered_surveys": unanswered_surveys,
            "current_time": current_time,
        },
    )


@login_required
@allowed_roles("admin")
def start_admin_view(request):
    return render(
        request, "start_admin.html", {"pagetitle": f"Välkommen<br>{request.user.name}"}
    )


@login_required
@allowed_roles("surveycreator", "surveyresponder")
def survey_result_view(request, survey_id):
    survey = models.Survey.objects.filter(id=survey_id).first()

    if survey is None:
        # This survey has no answers (should not even be displayed to the user then)
        return HttpResponse(400)

    # TODO : Change so gets analysis handler from organization
    analysis_handler = AnalysisHandler()

    # Retrievs all survey results of this survey
    survey_results = survey.survey_results.all()
    user = request.user

    # Check if user has answered this survey
    has_result: bool = survey_results.filter(user=user, is_answered=True).exists()

    # Check if user is the creator
    is_creator: bool = survey.creator == user

    summary_context = analysis_handler.get_survey_summary(survey.id)
    for summary in summary_context["summaries"]:
        summary["my_result"] = analysis_handler.get_answers(
            summary["question"], user=user, survey=survey
        ).first()

        if "text_answers" in summary and summary["text_answers"]:
            answers = list(summary["text_answers"])
            random.shuffle(answers)
            summary["text_answers"] = answers

    # Add context to summary_context
    summary_context["has_result"] = has_result
    summary_context["is_creator"] = is_creator

    if survey_results is None:
        # This survey has no answers (should not even be displayed to the user then)
        return HttpResponse(400)

    # Proceed to render the survey results
    return render(request, "survey_result.html", summary_context)


@login_required
@allowed_roles("surveycreator")
def survey_status_view(request):
    user = request.user
    published_count = user.published_surveys.count()

    # Order the surveys by deadline date (old before young)
    published_surveys_ordered = user.published_surveys.all().order_by("-deadline")

    return render(
        request,
        "survey_status.html",
        {
            "published_surveys": published_surveys_ordered,
            "current_time": timezone.now(),
            "published_count": published_count,
        },
    )


@login_required
@allowed_roles("surveycreator", "surveyresponder")
def unanswered_surveys_view(request):
    user = request.user  # Assuming the user is authenticated
    unanswered_count = user.count_unanswered_surveys()
    unanswered_surveys = user.get_unanswered_surveys()
    current_time = timezone.now()
    return render(
        request,
        "unanswered_surveys.html",
        {
            "unanswered_count": unanswered_count,
            "unanswered_surveys": unanswered_surveys,
            "pagetitle": "Obesvarade enkäter",
            "current_time": current_time,
            "user_role": user.user_role,
        },
    )


def find_organization_by_email(email: str) -> models.Organization | None:
    org = models.EmailList.objects.filter(email=email).exists()
    if not org:
        # No organization found
        return None
    email_entry = get_object_or_404(models.EmailList, email=email)
    return email_entry.org  # Follow the ForeignKey to Organization


def correct_name(name: str) -> Boolean | str:
    """
    Checks if the given name is on the correct form
    firstname lastname, i.e. with a blank space in between,
    and returns the name on the form Firstname Lastname (str), or
    False if the name is not correct.
    """
    res = ""
    # Split on the blank space
    first_last_name = name.split(" ")
    if len(first_last_name) == 1 or first_last_name[1] == "":
        # No blank space found or a blank space not followed by a last name
        return False
    else:
        # Turn the first character of every name to upper case
        for name in first_last_name:
            res += name.capitalize() + " "
        # Return the name with the correct form
        return res


@login_required
@allowed_roles("admin", "surveycreator")
def analysis_view(request):
    group_id = request.GET.get("group_id")
    survey_count = request.GET.get("surveys", "1")
    user_id = request.GET.get("user_id")
    question_id = request.GET.get("question_id")

    analysisHandler = AnalysisHandler()

    context = {
        "survey_ranges": [
            ("Senaste", "1"),
            ("Senaste 3", "3"),
            ("Senaste 5", "5"),
            ("Alla", "all"),
        ],
        "selected_survey_range": survey_count,
        "selected_user_id": user_id,
        "selected_question_id": question_id,
    }

    if not group_id:
        return render(request, "analysis.html", context)

    group = get_object_or_404(EmployeeGroup, id=group_id)
    surveys = analysisHandler.get_surveys_for_group(group)

    if not surveys.exists():
        context["message"] = "Gruppen har inga enkäter ännu."
        return render(request, "analysis.html", context)

    surveys = surveys.order_by("-sending_date")
    if survey_count != "all":
        try:
            count = int(survey_count)
            filtered_surveys = surveys[:count]
        except ValueError:
            filtered_surveys = surveys
    else:
        filtered_surveys = surveys

    if not filtered_surveys:
        context["message"] = "Inga filtrerade enkäter hittades."
        return render(request, "analysis.html", context)
    latest_survey = filtered_surveys[0]
    respondents_dict = analysisHandler.get_respondents(latest_survey, group)
    context["respondents"] = respondents_dict

    participation_metrics = analysisHandler.get_participation_metrics(
        list(filtered_surveys), group
    )
    print(participation_metrics)
    context["answerFrequencyData"] = [
        entry["answer_pct"] for entry in participation_metrics
    ]
    context["answer_pct"] = context["answerFrequencyData"][0]
    context["answerFrequencyLabels"] = [
        str(entry["survey"].sending_date) for entry in participation_metrics
    ]

    survey_answer_dist = analysisHandler.get_survey_answer_distribution(
        latest_survey,
        user=respondents_dict.get(user_id) if user_id else None,
        employee_group=group,
    )
    context["answerDistributionLabels"] = [
        entry["question"].question for entry in survey_answer_dist
    ]
    context["answerDistributionData"] = [
        entry["answered_count"] for entry in survey_answer_dist
    ]

    selected_question_format = None
    if question_id:
        selected_question = get_object_or_404(models.Question, id=question_id)
        context["selected_question_text"] = selected_question.question

        if selected_question.question_type == QuestionType.ENPS:
            selected_question_format = QuestionType.ENPS
        else:
            selected_question_format = selected_question.question_format

        # Trenddata för alla format
        trend_data = analysisHandler.get_question_trend(
            selected_question,
            list(filtered_surveys),
            group,
            respondents_dict.get(user_id) if user_id else None,
        )

        if trend_data:
            last_summary = trend_data[-1]["summary"]

            context["slider_mean"] = last_summary.get("mean", 0)
            context["slider_std"] = last_summary.get("standard_deviation", 0)
            context["slider_cv"] = last_summary.get("variation_coefficient", 0)
            context["slider_median"] = last_summary.get("median", 0)  # om tillgänglig

            context["slider_values"] = last_summary.get(
                "labels", [str(i) for i in range(11)]
            )
            context["sliderDistribution"] = last_summary.get("distribution", [0] * 11)
            context["sliderTrendData"] = [
                entry["summary"].get("mean", 0) for entry in trend_data
            ]
            context["sliderTrendLabels"] = [
                entry["sending_date"] for entry in trend_data
            ]

            context["enpsScore"] = last_summary.get("enpsScore")
            context["enpsPieLabels"] = last_summary.get("enpsPieLabels")
            context["enpsPieData"] = last_summary.get("enpsPieData")
            context["enpsDistribution"] = last_summary.get("enpsDistribution")

            context["multipleChoiceLabels"] = last_summary.get("answer_options")
            context["multipleChoiceData"] = last_summary.get("distribution")

            context["yesNoLabels"] = last_summary.get("answer_options")
            context["yesNoData"] = last_summary.get("distribution")

    context["selected_question_format"] = selected_question_format
    context["bank_questions"] = analysisHandler.get_bank_questions()
    context["QuestionFormat"] = QuestionFormat
    context["QuestionType"] = QuestionType

    return render(request, "analysis.html", context)
