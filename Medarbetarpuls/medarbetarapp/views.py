from . import models
import platform
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import SurveyResult
from django.core.mail import send_mail
from django.core.cache import cache
from datetime import datetime, time
from django.utils.timezone import make_aware
from django.db.models import Count
from django.db.models import Case, When, IntegerField, Value
from .tasks import publish_survey_async

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
    Saves potential account information in django 
    session from fetched input, it sends an email 
    to the mail that has been fetched. 
    Then redirect to authentication-acc to 
    authenticate and potentially create account.

    Args:
        request: The input text from the name, email and password fields

    Returns:
        HttpResponse: Redirects to authentication page, otherwise error message 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            from_settings = request.POST.get('from_settings') == 'true'
            code = 123456 # make random later, just test now
            cache.set(f'verify_code_{email}', code, timeout=300)
            send_mail(
                subject='Your Verification Code',
                message=f'Your verification code is: {code}',
                from_email='medarbetarpuls@gmail.com',
                recipient_list=[email],
                fail_silently=False,
            )
            # Save potential user account data in session
            request.session['user_data'] = {
                'name': name,
                'password': password,
                'from_settings': from_settings,
            }

            # Save the mail where the two factor code is sent
            request.session['email_two_factor_code'] = email

            return HttpResponse(headers={"HX-Redirect": "/authentication-acc/"})  # Redirect to authentication account page

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
        request: The input text from the authentication code field

    Returns:
        HttpResponse: Returns status 204 if all is good, otherwise 400
    """

    if request.method == "POST":
        email = request.POST.get("email")
        team = request.POST.get("team")
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
                if models.EmployeeGroup.objects.filter(name=team).exists():
                    group = models.EmployeeGroup.objects.get(name=team)
                else:
                    #create new employee group
                    group = models.EmployeeGroup(name=team, organization=org)
                    group.save()
                email_instance = models.EmailList(email=email, org=org)
                email_instance.save()
                email_instance.employee_groups.add(group)
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
def answer_survey_view(request, survey_result_id, question_index=0):
    survey = get_object_or_404(SurveyResult, pk=survey_result_id, user=request.user)
    questions = survey.published_survey.questions.all()

    if question_index >= len(questions):
        # All questions answered, redirect somewhere else
        survey.is_answered = True
        survey.save()
        return redirect("start_user")  # or a summary page

    question = questions[question_index]

    if request.method == "POST":
        if "slider" in request.POST:
            # Returns the object with Boolean 'created', which says if a new object was created
            answer, created = models.Answer.objects.get_or_create(survey=survey, question=question, slider_answer=request.POST.get("slider"))

        elif "text" in request.POST:
            answer, created = models.Answer.objects.get_or_create(survey=survey, question=question, free_text_answer=request.POST.get("text"))
        
        elif "yesno" in request.POST:
            answer, created = models.Answer.objects.get_or_create(survey=survey, question=question, yes_no_answer=request.POST.get("yesno"))
        
        elif "multiplechoice" in request.POST:
            answer, created = models.Answer.objects.get_or_create(survey=survey, question=question, multiple_choice_answer=request.POST.get("multiplechoice"))
            
        answer.is_answered = True
        answer.save()
        return redirect("answer_survey", survey_result_id=survey.id, question_index=question_index + 1)

    return render(request, "answer_survey.html", {
        "question": question,
        "question_index": question_index,
        "total": len(questions),
        "survey_result_id": survey.id,
    })

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
    if request.method == 'POST':
        auth_code = request.POST.get('auth_code')
        email = request.session.get('email_two_factor_code')
        expected_code = cache.get(f'verify_code_{email}')

        if str(auth_code) == str(expected_code):
            data = request.session.get('user_data')
            name=data['name']
            password=data['password']
            from_settings = data['from_settings']

            # Delete everything saved in session and cache - data not needed anymore
            del request.session['user_data']
            del request.session['email_two_factor_code']
            cache.delete(f'verify_code_{email}')
            
            existing_user = models.CustomUser.objects.filter(email=email).first()
            if existing_user and str(from_settings)=='true': #and coming from settings page
                # Should they be able to reset name and password???
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
                group =  email_from_list.employee_groups.all()
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

    if request.method == 'POST':
        auth_code = request.POST.get('auth_code')
        email = request.session.get('email_two_factor_code_org')
        expected_code = cache.get(f'verify_code_{email}')
        if str(auth_code) == str(expected_code):

            data = request.session.get('user_org_data')
            org_name = str(data['org_name'])
            name = str(data['name'])
            password = str(data['password'])

            del request.session['user_org_data']
            del request.session['email_two_factor_code_org']
            cache.delete(f'verify_code_{email}')

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


def create_org_view(request):
    return render(request, "create_org.html")


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
    survey_temp: models.SurveyTemplate = user.survey_templates.filter(id=survey_id).first()
    if survey_temp is None:
        # Handle the case where the survey template does not exist
        return HttpResponse("Survey template not found", status=404)
    
    return render(request, "create_question.html", 
                  {"survey_temp": survey_temp, 
                   "QuestionFormat": models.QuestionFormat,
                   })


def create_org_redirect(request):
    if request.headers.get("HX-Request"):
        return HttpResponse(
            headers={"HX-Redirect": "/create_org_view/"}
        )  # Redirects in HTMX

    return redirect("/create_org_view/")  # Normal Django redirect for non-HTMX requests


@csrf_protect
def create_org(request) -> HttpResponse:
    """
    Saves potential account information in django 
    session from fetched input, it sends an email 
    to the mail that has been fetched. 
    Then redirect to authentication-org to 
    authenticate and potentially create admin account.

    Args:
        request: The input text from the org_name, name, email and password fields

    Returns:
        HttpResponse: Redirects to authentication page, otherwise error message 400
    """
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            org_name = request.POST.get("org_name")
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            code = 123456 # make random later, just test now
            cache.set(f'verify_code_{email}', code, timeout=300)
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

            return HttpResponse(headers={"HX-Redirect": "/authentication-org/"})  # Redirect to authentication account page
        
    return HttpResponse(status=400)  # Bad request if no expression


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
            question: models.Question = get_object_or_404(models.Question, id=question_id)
            question.delete()
            return HttpResponse(headers={"HX-Redirect": "/create-survey/" + str(survey_id)})  
    
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
        survey_temp: models.SurveyTemplate = models.SurveyTemplate(creator=request.user, last_edited=timezone.now())
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
    survey_temp: models.SurveyTemplate = user.survey_templates.filter(id=survey_id).first()
    if survey_temp is None:
        # Handle the case where the survey template does not exist
        return HttpResponse("Survey template not found", status=404)
    
    # Redirect to publish survey
    if request.method == "GET":
        if request.headers.get("HX-Request"):
            return HttpResponse(headers={"HX-Redirect": "/create-survey/" + str(survey_id) + "?trigger_popup=true"})  

    return render(request, "create_survey.html", {"survey_temp": survey_temp})


def edit_question_view(request, survey_id: int, question_format: models.QuestionFormat, question_id: str | None = None) -> HttpResponse:
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
    
    # Get the survey from given id
    survey_temp: models.SurveyTemplate = user.survey_templates.filter(id=survey_id).first()
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
            if question_format not in [choice.value for choice in models.QuestionFormat]:
                return HttpResponse("Invalid question type", status=404)
            
            # Specify question format
            question.question_format = question_format 
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

    return render(request, "edit_question.html", {"survey_temp": survey_temp, "question_format": question_format, "question_id": question_id, "question_text": question_text})


def publish_survey(request, survey_id: int) -> HttpResponse: 
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            # Fetch the corresponding survey template by survey id
            # from the database and render the create_survey view
            user: models.CustomUser = request.user
            survey_temp: models.SurveyTemplate = user.survey_templates.filter(id=survey_id).first()
            if survey_temp is None:
                # Handle the case where the survey template does not exist
                return HttpResponse("Survey template not found", status=404)

            # Get the input information:

            # Privacy checkboxes (can have multiple selected)
            privacy_choices = request.POST.getlist('privacy')  # returns list like ['anonymous', 'public']
            is_anonymous: bool = 'anonymous' in privacy_choices  
            is_public: bool = 'public' in privacy_choices       

            # Survey name
            survey_name: str = request.POST.get('survey-name')

            # Get the receiving employee group
            employee_group_name: str = request.POST.get('send-to')
            employee_group: models.EmployeeGroup = user.survey_groups.filter(name=employee_group_name).first() 

            # Handle the case where no employee group was found 
            if employee_group is None: 
                return render(request, "partials/error_message.html", {"message": "Felaktig arbetsgrupp vald!"})

            # Get the dates 
            publish_date: str = request.POST.get('publish-date')  
            end_date: str = request.POST.get('end-date')         

            # Make the dates timezone aware to keep django from complaining
            if end_date:
                naive_deadline = datetime.combine(
                    datetime.strptime(end_date, "%Y-%m-%d").date(),
                    time(hour=23, minute=55)
                )
                deadline = make_aware(naive_deadline)  # Now it's timezone-aware
            else: 
                deadline = None

            if publish_date:
                naive_sending_date = datetime.combine(
                    datetime.strptime(publish_date, "%Y-%m-%d").date(),
                    time(hour=0, minute=5)
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
                        {"message": "Sista svarsdatum måste vara efter publiceringsdatum"},
                        status=200
                    )
            else:
                return render(
                    request,
                    "partials/error_message.html",
                    {"message": "Publiceringsdatum och sista svarsdatum måste anges"},
                    status=200
                )

            # Create a Survey to be send to employess
            survey: models.Survey = models.Survey(name=survey_name, creator=user, deadline=deadline, sending_date=sending_date, is_viewable=is_public) 
            survey.save()
            survey.employee_groups.add(employee_group)
            survey.save()

            # Copy all questions from the template to the survey
            survey.questions.set(survey_temp.questions.all())
            survey.save()

            # Only tries scheduling if we are on linux system!
            os_type = platform.system()

            if os_type == "Linux": 
                publish_survey_async.apply_async(args=[survey.id], eta=survey.sending_date)
            else:
                survey.publish_survey()

            return HttpResponse(headers={"HX-Redirect": "/create-survey/" + str(survey_id)})  

    return HttpResponse(status=400)  

 
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


@csrf_protect
def delete_survey_template(request, survey_id: int) -> HttpResponse:
    if request.method == "POST":  
        if request.headers.get("HX-Request"):
            survey_temp = get_object_or_404(models.SurveyTemplate, id=survey_id, creator=request.user)
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
    empty_templates: models.SurveyTemplate = request.user.survey_templates.annotate(num_questions=Count("questions")).filter(num_questions=0)

    # Delete them
    empty_templates.delete()

    if search_str is None: 
        # Order templates by last time edited
        survey_templates = request.user.survey_templates.all().order_by('-last_edited')
    else: 
        # Order templates by search bar input relevance 
        survey_templates = request.user.survey_templates.annotate(
            relevance=Case(
            When(name__iexact=search_str, then=Value(3)),  # exact match
            When(name__istartswith=search_str, then=Value(2)),  # startswith
            When(name__icontains=search_str, then=Value(1)),  # somewhere inside
            default=Value(0),
            output_field=IntegerField()
            )
        ).order_by('-relevance', '-last_edited')

    # Post request for when search button is pressed
    if request.method == "POST":  
        if request.headers.get("HX-Request"):
            search_str_input: str = request.POST.get("search-bar")

            if search_str_input is None: 
                return HttpResponse(headers={"HX-Redirect": "/templates_and_drafts/"})  
            else: 
                return HttpResponse(headers={"HX-Redirect": "/templates_and_drafts/" + search_str_input})  
    
    return render(request, "templates_and_drafts.html", {"survey_templates": survey_templates})



@login_required 
def my_surveys_view(request):
    return render(request, "my_surveys.html")


def settings_admin_view(request):
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
                user.delete() #maybe not right because we want the users answers to be saved still
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

                #models.EmailList.objects.filter(email = newAdminEmail, org=org).delete() MAYBE should delete this from emaillist because the account is now admin
                new_admin.save()
                logout(request)
                return HttpResponse(headers={"HX-Redirect": "/"})
            else: 
                logger.error(" The mail entered is not an available user ")
                return HttpResponse(status=400)

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

    
    #Delete user function
    # if pressed delete user
    if request.method == "POST":
        if request.headers.get("HX-Request"):
            password = request.POST.get("password")
            email = request.user.email
            # Check so password is correct
            user = authenticate(request, username=email, password=password)
            if user is not None:
                #set user to inactive and save then logout the user
                #user.is_active = False
                #user.save()

                user.delete() #maybe not right because we want the users answers to be saved still
                logout(request)
                return HttpResponse(headers={"HX-Redirect": "/"})
            else:  
                logger.error("Wrong password entered")
                return HttpResponse(status=400)
    return render(request, "settings_user.html", {"user": request.user})

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
