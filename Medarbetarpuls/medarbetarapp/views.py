import logging
import platform
from . import models
from django.db.models import Q
from collections import Counter
from django.utils import timezone
from django.db.models import Count
from django.core.cache import cache
from datetime import datetime, time
from django.http import HttpResponse
from .models import SurveyUserResult
from django.core.mail import send_mail
from .tasks import publish_survey_async
from django.utils.timezone import make_aware
from .analysis_handler import AnalysisHandler
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, IntegerField, Value
from .models import Answer, Question, Survey, SurveyUserResult
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash



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
        email = request.POST.get("email")
        password = request.POST.get("password")
        from_settings = request.POST.get("from_settings") == "true"

        org = find_organization_by_email(email=email)
        if org is None:
            logger.error("This email is not authorized for registration.")
            return HttpResponse(status=400)

        code = 123456   # make random later, just test now
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
            "name": name,
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
@csrf_exempt
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
        if(editGroup == "true"):
            if models.EmailList.objects.filter(email=editUserMail).exists():
                org = user.admin
                if models.EmployeeGroup.objects.filter(name=editName).exists():
                        group = models.EmployeeGroup.objects.get(name=editName)
                else:
                    #create new employee group
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
                        group = models.EmployeeGroup.objects.get(name=team)
                    else:
                        # create new employee group
                        group = models.EmployeeGroup(name=team, organization=org)
                        group.save()
                    email_instance = models.EmailList(email=email, org=org)
                    email_instance.save()
                    email_instance.employee_groups.add(group)
                    user.survey_groups.add(group)
                else:
                    logger.error("Existing user already have an active account")
                    pass
                    # Vad gör vi med folk som vill bli registerade till 2 organisationer

            else:
                if models.EmployeeGroup.objects.filter(name=team).exists():
                    group = models.EmployeeGroup.objects.get(name=team)
                else:
                    # create new employee group
                    group = models.EmployeeGroup(name=team, organization=org)
                    group.save()
                email_instance = models.EmailList(email=email, org=org)
                email_instance.save()
                email_instance.employee_groups.add(group)
                user.survey_groups.add(group)
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
@csrf_protect
def answer_survey_view(request, survey_result_id: int, question_index: int = 0) -> HttpResponse:
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
    survey_result: models.SurveyUserResult = get_object_or_404(SurveyUserResult, pk=survey_result_id, user=user)
    questions: list[models.Question] = survey_result.published_survey.questions.all()
    answers: list[models.Answer] = survey_result.answers.all()
    answer: models.Answer = models.Answer()
    
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
                answer = models.Answer(survey=survey_result, question=question, slider_answer=5.0)
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
                if submit_answers == "1": 
                    survey_result.is_answered = True
                    survey_result.published_survey.collected_answer_count += 1 
                    survey_result.published_survey.save()
                    survey_result.save()

                    # Redirect to unanswered surveys page after completion
                    return HttpResponse(headers={"HX-Redirect": "/unanswered-surveys/"})  
                
                # Redirect to next question
                return HttpResponse(headers={"HX-Redirect": "/survey/" + str(survey_result.id) + "/question/" + str(question_index+1)})  
            
            return HttpResponse(status=400)

    # This is added so a "double" loop can be used to go through 
    # which boxes should be checked
    if question.multiple_choice_question is not None: 
        # Edge case where no answer yet exists, but we still 
        # want to display the options...
        if not answer.multiple_choice_answer: 
            zipped = zip(question.multiple_choice_question.options, [False, False, False, False])
        else: 
            zipped = zip(question.multiple_choice_question.options, answer.multiple_choice_answer)
    else: 
        zipped = None

    # Calculate amount of "answered" answers
    # Start at 1 because the last question always gets a saved answer
    # that is not counted
    total_answers: int = 1
    for ans in answers: 
        if ans.is_answered:  
            total_answers += 1

    return render(request, "answer_survey.html", {
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
    })

@csrf_exempt
def resend_authentication_code_acc(request):
    if request.method == "POST":
        source = request.POST.get("source")
        email = "not_defined"
        if(source=="from_account"):
            print("from_account")
            email = request.session.get("email_two_factor_code")
        elif(source=="from_org"):
            print("from_org")
            email = request.session.get("email_two_factor_code_org")
        if email == "not_defined":
            return HttpResponse("No email defined", 404)
        print("here")
        code = 654321 # make random later, just test now
        cache.set(f'verify_code_{email}', code, timeout=300)

        #Send email with the code to the user
        send_mail(
            subject='Your Verification Code',
            message=f'Your verification code is: {code}',
            from_email='medarbetarpuls@gmail.com',
            recipient_list=[email],
            fail_silently=False,
        )
        return HttpResponse("Sent", 200)



@csrf_exempt
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
            data = request.session.get('user_data')
            name=data['name']
            password=data['password']

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
                    return HttpResponse(status=400)
                existing_user.is_active = True
                existing_user.name = name
                existing_user.set_password(password)
                existing_user.save()
                return HttpResponse(headers={"HX-Redirect": "/"})
                # check for basegroup??
            else:
                # Check that email is registrated to an org
                org = find_organization_by_email(email)
                if org is None:
                    logger.error("This email is not authorized for registration.")
                    return HttpResponse(status=400)
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

                return HttpResponse(headers={"HX-Redirect": "/"})
        else:
            logger.error("Wrong authentication code")
            return HttpResponse(status=400)
    
    return render(request, "authentication_acc.html")


@csrf_exempt
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

            return HttpResponse(headers={"HX-Redirect": "/"})
        else:
            logger.error("Wrong authentication code")
            return HttpResponse(status=400)

    return render(request, "authentication_org.html")

def create_question(request, survey_id: int) -> HttpResponse: 
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
    # Retrieve the survey template from the database if it belongs to the user
    survey_temp: models.SurveyTemplate = user.survey_templates.filter(
        id=survey_id
    ).first()
    if survey_temp is None:
        # Handle the case where the survey template does not exist
        return HttpResponse("Survey template not found", status=404)

    return render(
        request,
        "create_question.html",
        {
            "survey_temp": survey_temp,
            "QuestionFormat": models.QuestionFormat,
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
        for GET, sends HX-Redirect header or renders "create_org.html".
    """
    
    if request.method == "POST":
        #Get data from the forum
        org_name = request.POST.get("org_name")
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")


        code = 123456 # make random later, just test now
        cache.set(f'verify_code_{email}', code, timeout=300)

        #Send email with the code to the user
        send_mail(
            subject='Your Verification Code',
            message=f'Your verification code is: {code}',
            from_email='medarbetarpuls@gmail.com',
            recipient_list=[email],
            fail_silently=False,
        )

        # Save potential user account data in session
        request.session['user_org_data'] = {
            'org_name': org_name,
            'name': name,
            'password': password,
        }
        # Save the mail where the two factor code is sent
        request.session['email_two_factor_code_org'] = email

        # Redirect to authentication
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/authentication-org/"})
        return redirect("/authentication-org/")
    
    else:
        # GET-request: render or redirect to create_org
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/create_org/"})
        return render(request, "create_org.html")
    
    #maybe implement error 400??


@csrf_protect
def delete_question(request, question_id: int, survey_id: int) -> HttpResponse:
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
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            question: models.Question = get_object_or_404(
                models.Question, id=question_id
            )
            question.delete()
            return HttpResponse(
                headers={"HX-Redirect": "/create-survey/" + str(survey_id)}
            )

    return HttpResponse(status=400)  # Bad request if no expression


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

    # Check if survey_id is not given
    if survey_id is None:
        # Create a new survey template and assign it to the user
        survey_temp: models.SurveyTemplate = models.SurveyTemplate(
            creator=request.user, last_edited=timezone.now()
        )
        survey_temp.save()
        # Set a placeholder name for the survey
        survey_id = survey_temp.id
        survey_temp.name = "Survey " + str(survey_id)
        survey_temp.save()

        # Redirect to the create_survey view with the new survey_id
        # This will allow the user to edit the survey template immediately
        return redirect("create_survey_with_id", survey_id=survey_temp.id)

    # If survey_id is given, fetch the corresponding survey template
    # from the database and render the create_survey view
    user: models.CustomUser = request.user
    survey_temp: models.SurveyTemplate = user.survey_templates.filter(
        id=survey_id
    ).first()
    if survey_temp is None:
        # Handle the case where the survey template does not exist
        return HttpResponse("Survey template not found", status=404)

    # Redirect to publish survey
    if request.method == "GET":
        if request.headers.get("HX-Request"):
            return HttpResponse(
                headers={
                    "HX-Redirect": "/create-survey/"
                    + str(survey_id)
                    + "?trigger_popup=true"
                }
            )

    return render(request, "create_survey.html", {"survey_temp": survey_temp})


def edit_question_view(
    request,
    survey_id: int,
    question_format: models.QuestionFormat,
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
    options = None # Use later to show options
    
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
                survey_temp.questions.add(question)
            else:
                question = survey_temp.questions.filter(id=question_id).first()

            # Check for valid question format
            if question_format not in [
                choice.value for choice in models.QuestionFormat
            ]:
                return HttpResponse("Invalid question type", status=404)

            # Specify question format
            question.question_format = question_format 
            question.save()

            # Add testcase for multiplechoice questions
            if question_format == models.QuestionFormat.MULTIPLE_CHOICE: 
                options = request.POST.getlist('options')
                for option in options:
                    if not option:
                        options.remove(option)
                # This is kinda fucked and can maybe be re-written better
                question.multiple_choice_question = models.MultipleChoiceQuestion(question_format=question_format)
                question.multiple_choice_question.save()
                question.multiple_choice_question.options.extend(options)
                question.multiple_choice_question.save()
                question.save()

            # Add question text
            question.question = request.POST.get("question")
            question.save()

            # Update last edited date of survey
            survey_temp.last_edited = timezone.now()
            survey_temp.save()

            return HttpResponse(headers={"HX-Redirect": "/create-survey/" + str(survey_id)})  

    # Checks if there is a specific question text to be displayed
    question_text: str | None = None
    if question_id is not None:
        question_text = models.Question.objects.filter(id=question_id).first().question
        if models.Question.objects.filter(id=question_id).first().multiple_choice_question:
            options = models.Question.objects.filter(id=question_id).first().multiple_choice_question.options

    return render(request, "edit_question.html", {"survey_temp": survey_temp, "question_format": question_format, "question_id": question_id, "question_text": question_text, "options": options})


def publish_survey(request, survey_id: int) -> HttpResponse:
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            # Fetch the corresponding survey template by survey id
            # from the database and render the create_survey view
            user: models.CustomUser = request.user
            survey_temp: models.SurveyTemplate = user.survey_templates.filter(
                id=survey_id
            ).first()
            if survey_temp is None:
                # Handle the case where the survey template does not exist
                return HttpResponse("Survey template not found", status=404)

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
                    {"message": "Felaktig arbetsgrupp vald!"},
                )

            # Get the dates
            publish_date: str = request.POST.get("publish-date")
            end_date: str = request.POST.get("end-date")

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

            # Ensure dates have been set correctly
            if sending_date and deadline:
                if deadline <= sending_date:
                    return render(
                        request,
                        "partials/error_message.html",
                        {
                            "message": "Sista svarsdatum måste vara efter publiceringsdatum"
                        },
                        status=200,
                    )
            else:
                return render(
                    request,
                    "partials/error_message.html",
                    {"message": "Publiceringsdatum och sista svarsdatum måste anges"},
                    status=200,
                )

            # Create a Survey to be send to employess
            survey: models.Survey = models.Survey(
                name=survey_name,
                creator=user,
                deadline=deadline,
                sending_date=sending_date,
                is_viewable=is_public,
                is_anonymous=is_anonymous,
            )
            survey.save()
            survey.employee_groups.add(employee_group)
            survey.save()

            # Copy all questions from the template to the survey
            survey.questions.set(survey_temp.questions.all())
            survey.save()

            # Only tries scheduling if we are on linux system!
            os_type = platform.system()

            if os_type == "Linux":
                publish_survey_async.apply_async(
                    args=[survey.id], eta=survey.sending_date
                )
            else:
                survey.publish_survey()

            return HttpResponse(
                headers={"HX-Redirect": "/create-survey/" + str(survey_id)}
            )

    return HttpResponse(status=400)


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
        user_id = request.POST.get("user_id")
        if request.user.user_role == models.UserRole.ADMIN:
            employee_to_remove = models.CustomUser.objects.get(pk=user_id)
            print("removing ", employee_to_remove)
            employee_to_remove.is_active = False
            employee_to_remove.save()
            # Get all employee_groups for this employee
            all_groups = employee_to_remove.employee_groups.all()
            # Remove all other groups except "Alla"
            group_to_keep = models.EmployeeGroup.objects.get(name="Alla")
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

    # Fånga sökterm
    search_query = request.GET.get("search", "")
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query) | Q(email__icontains=search_query)
        )

    # Kolla om detta är en HTMX-request
    if "HX-Request" in request.headers:
        # Returnera bara tabell-rader
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
        },
    )


@csrf_protect
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
    if request.method == "POST":  
        if request.headers.get("HX-Request"):
            survey_temp = get_object_or_404(
                models.SurveyTemplate, id=survey_id, creator=request.user
            )
            survey_temp.delete()
            return HttpResponse(headers={"HX-Redirect": "/templates_and_drafts/"})

    return HttpResponse(status=400)


@csrf_protect
@login_required
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
        request, "templates_and_drafts.html", {"survey_templates": survey_templates}
    )


@login_required
def my_surveys_view(request):
    return render(request, "my_surveys.html")


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
    #Leave over account to new admin function
    # if pressed leave over account
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            # get new admins mail
            new_admin_email = request.POST.get("email")
            # get old admin and the organisation
            user = request.user
            org = user.admin

            # check if new email exist and then switch roles and save
            if models.EmailList.objects.filter(email=new_admin_email).exists():
                """user.is_active = False
                user.is_superuser = False
                user.admin = None
                user.user_role = models.UserRole.SURVEY_RESPONDER
                user.save()"""
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
    #Delete user function
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

                user.delete()  # maybe not right because we want the users answers to be saved still
                logout(request)
                return HttpResponse(headers={"HX-Redirect": "/"})
            else:
                logger.error("Wrong password entered")
                return HttpResponse(status=400)
    return render(request, "settings_user.html", {"user": request.user})


@login_required
def start_creator_view(request):
    return render(
        request, "start_creator.html", {"pagetitle": f"Välkommen<br>{request.user.name}"}
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
        check_password = request.POST.get("pass_check")  # The repeated new password
        user = authenticate(request, username=request.user.email, password=old_password)
        # Check that the old password is correct and that the new password is repeated
        if user and check_password == new_password:
            user.set_password(new_password)
            user.save()
            # Use this to keep the session alive (avoid being logged out immediately)
            update_session_auth_hash(request, user)
            print("saved new password")
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
def start_user_view(request):
    return render(
        request, "start_user.html", {"pagetitle": f"Välkommen<br>{request.user.name}"}
    )

@login_required
def start_admin_view(request):
    return render(
        request, "start_admin.html", {"pagetitle": f"Välkommen<br>{request.user.name}"}
    )


def survey_result_view(request, survey_id):
    survey_results = SurveyUserResult.objects.filter(id=survey_id).first()

    # TODO: some analysis here before sending to survey_result?

    if survey_results is None:
        # This survey has no answers (should not even be displayed to the user then)
        return HttpResponse(400)

    # Proceed to render the survey results
    return render(request, "survey_result.html", {"survey_result": result}) #result ??


@login_required
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
        },
    )

def find_organization_by_email(email: str) -> models.Organization | None:
    email_entry = get_object_or_404(models.EmailList, email=email)
    return email_entry.org  # Follow the ForeignKey to Organization

def chart_view(request):
    SURVEY_ID = 3  # Choose which survey to show here

    analysisHandler = AnalysisHandler()
    question_txt = "Did you take enough breaks throughout the day?"
    context = analysisHandler.survey_result_summary(SURVEY_ID)
    return render(request, "analysis.html", context)


def chart_view_test(request):
    # If no real data exists, show sample data
    labels = ["Happy", "Neutral", "Sad"]
    data = [3, 2, 1]

    context = {
        "labels": labels,
        "data": data,
    }

    return render(request, "analysis.html", context)
