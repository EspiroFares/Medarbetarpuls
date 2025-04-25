from django.db import models, transaction
from django.core.mail import send_mail
from django.db.models.manager import BaseManager
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
import logging
from typing import cast

# from .analysis_handler import AnalysisHandler

logger = logging.getLogger(__name__)

# Define explicit type aliases to help with readability
OneToManyManager = BaseManager  # Alias for ForeignKey reverse relations
ManyToManyManager = BaseManager  # Alias for ManyToManyField relations


class Organization(models.Model):
    name = models.CharField(max_length=255)
    # Add an explicit type hint for employeeGroups (this is just for readability)
    employee_groups: OneToManyManager["EmployeeGroup"]
    admins: OneToManyManager["CustomUser"]
    # Logo: How do we want to save this???
    question_bank: OneToManyManager["Question"]
    survey_template_bank: OneToManyManager["SurveyTemplate"]
    org_emails = OneToManyManager["EmailList"]

    def __str__(self) -> str:
        return f"{self.name} | Admins: {', '.join(str(admin) for admin in self.admins.all())}"


class EmployeeGroup(models.Model):
    name = models.CharField(max_length=255)
    employees: ManyToManyManager["CustomUser"]
    managers: ManyToManyManager["CustomUser"]

    # Relationships to parent classes
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="employee_groups",
        null=True,
    )

    def __str__(self) -> str:
        return f"{self.name} {self.organization.name}"


# Enum class for user roles
# The left-most string is what is saved in db
# The right-most string is what we humans will read
class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    SURVEY_CREATOR = "surveycreator", "SurveyCreator"
    SURVEY_RESPONDER = "surveyresponder", "SurveyResponder"


# Custom User Manager
# This Mananger is required for Django to be able to handle
# the CustomUser class
class CustomUserManager(BaseUserManager):
    def create_user(
        self, email: str, name: str, password: str, **extra_fields
    ) -> "CustomUser":
        """
        This function creates a new user and saves it in db

        Args:
            email (str): The email for the new user
            name (str): The name for the new user
            password (str): The password for the new user
            extra_fields (**): Extra fields to add more attributes

        Returns:
            CustomUser:
        """
        if not email:
            logger.error("The email field must be set")
            raise ValueError("The email field must be set")
        if not name:
            logger.error("The name field must be set")
            raise ValueError("The name field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)  # Hashes the password
        user.save(using=self._db)
        return user


# The actual custom user class
class CustomUser(AbstractBaseUser, PermissionsMixin):  # pyright: ignore
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    user_role = models.CharField(
        max_length=15, choices=UserRole.choices, default=UserRole.SURVEY_RESPONDER
    )
    # We deafult to 0 as the lowest level of authority
    authorization_level = models.IntegerField(default=0)  # pyright: ignore
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name="employees")
    survey_results = OneToManyManager["SurveyUserResult"]
    survey_groups = models.ManyToManyField(EmployeeGroup, related_name="managers")
    survey_templates = OneToManyManager["SurveyTemplate"]
    published_surveys = OneToManyManager["Survey"]

    # Relationships to parent classes
    admin = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="admins", null=True
    )

    # These are for the built-in django permissions!!!
    is_staff = models.BooleanField(
        default=False  # pyright: ignore
    )  # Allows access to admin panel
    is_superuser = models.BooleanField(
        default=False  # pyright: ignore
    )  # Allows you to do something in the admin panel
    is_active = models.BooleanField(
        default=True  # pyright: ignore
    )  # Controls if the user can log in

    objects = CustomUserManager()

    USERNAME_FIELD = "email"  # Use email instead of username when searching through db

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"

    # To see how many surveys this user has unanswered
    def count_unanswered_surveys(self):
        return self.survey_results.filter(is_answered=False).count()

    # To see how many surveys this user has answered
    def count_answered_surveys(self):
        return self.survey_results.filter(is_answered=True).count()

    # To get all unanswered surveys for this user
    def get_unanswered_surveys(self):
        return self.survey_results.filter(is_answered=False)

    # To get all answered surveys for this user
    def get_answered_surveys(self):
        return self.survey_results.filter(is_answered=True)


# Below are models for surveys and their results


# Enum class for questions types
# The left-most string is what is saved in db
# The right-most string is what we humans will read
class QuestionType(models.TextChoices):
    ONETIME = "onetime", "Onetime"
    REOCCURRING = "reoccurring", "Reoccurring"
    BUILTIN = "builtin", "Built in"
    ENPS = "enps", "ENPS"


# Enum class for questions formats
# The left-most string is what is saved in db
# The right-most string is what we humans will read
class QuestionFormat(models.TextChoices):
    MULTIPLE_CHOICE = "multiplechoice", "Multiple choice"
    YES_NO = "yesno", "Yes No"
    TEXT = "text", "Text"
    SLIDER = "slider", "Slider"


# What this model does needs to be explained here
class Survey(models.Model):
    name = models.CharField(max_length=255)  # Do we want names for surveys???
    questions = ManyToManyManager["Question"]
    creator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="published_surveys",
        null=True,
    )
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name="+")
    survey_results: OneToManyManager["SurveyUserResult"]
    deadline = (
        models.DateTimeField()
    )  # stores both date and time (e.g., YYYY-MM-DD HH:MM:SS)
    sending_date = (
        models.DateTimeField()
    )  # stores both date and time (e.g., YYYY-MM-DD HH:MM:SS)
    collected_answer_count = models.IntegerField(default=0)  # pyright: ignore
    published_count = models.IntegerField(default=0)  # pyright: ignore
    is_viewable = models.BooleanField(default=True)  # pyright: ignore
    is_anonymous = models.BooleanField(default=True)  # pyright: ignore

    def __str__(self) -> str:
        return f"{self.name} ({self.creator})"

    def publish_survey(self):
        """
        Publishes the survey to all employees in all
        employee groups linked to this survey
        """
        seen_employees = set()
        count: int = 0

        for group in self.employee_groups.all():
            for employee in group.employees.all():
                if employee.id not in seen_employees:
                    SurveyUserResult.objects.create(
                        published_survey=self, user=employee
                    )
                    seen_employees.add(employee)
                    count += 1

        # Saves the amount of users this survey has been sent to
        self.published_count = count
        self.save()

        # Send email to notify
        send_mail(
            subject="Ny obesvaradenkät",
            message="Det finns en ny enkät att svara på i Medarbetarpuls",
            from_email="medarbetarpuls@gmail.com",
            recipient_list=[employee.email for employee in seen_employees],
            fail_silently=False,
        )


# What this model does needs to be explained here
class SurveyTemplate(models.Model):
    name = models.CharField(max_length=255)  # Do we want names for surveyTemplates???
    questions = ManyToManyManager["Question"]
    creator = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="survey_templates", null=True
    )
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name="+")
    last_edited = (
        models.DateTimeField()
    )  # stores both date and time (e.g., YYYY-MM-DD HH:MM:SS)

    # Relationships to parent classes
    bank_survey = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="survey_template_bank",
        null=True,
    )

    def get_ordered_questions(self):
        return self.questions.all().order_by('questionorder__order')

    def __str__(self) -> str:
        return f"{self.name} ({self.creator})"


# What this model does needs to be explained here
class SurveyUserResult(models.Model):
    published_survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="survey_results", null=True
    )
    answers: OneToManyManager["Answer"]
    is_answered = models.BooleanField(default=False)  # pyright: ignore

    # Relationships to parent classes
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="survey_results", null=True
    )

    def __str__(self) -> str:
        return f"{self.user} ({self.is_answered})"


class BaseQuestionDetails(models.Model):
    parent_question = BaseManager["Question"]

    class Meta:
        abstract = True


# What this model does needs to be explained here
class SliderQuestion(BaseQuestionDetails):
    question_format = models.CharField(
        max_length=15, choices=QuestionFormat.choices, default=QuestionFormat.SLIDER
    )
    max_interval = models.IntegerField(default=10)  # pyright: ignore
    min_interval = models.IntegerField(default=0)  # pyright: ignore
    max_text = models.CharField(max_length=255)
    min_text = models.CharField(max_length=255)


# What this model does needs to be explained here
class MultipleChoiceQuestion(BaseQuestionDetails):
    question_format = models.CharField(
        max_length=15,
        choices=QuestionFormat.choices,
        default=QuestionFormat.MULTIPLE_CHOICE,
    )
    options = models.JSONField(default=list)  # Stores a list of strings


# What this model does needs to be explained here
class YesNoQuestion(BaseQuestionDetails):
    question_format = models.CharField(
        max_length=15, choices=QuestionFormat.choices, default=QuestionFormat.YES_NO
    )


# What this model does needs to be explained here
class TextQuestion(BaseQuestionDetails):
    question_format = models.CharField(
        max_length=15, choices=QuestionFormat.choices, default=QuestionFormat.TEXT
    )


# What this model does needs to be explained here
class Question(models.Model):
    question = models.CharField(max_length=255)
    question_format = models.CharField(
        max_length=15, choices=QuestionFormat.choices, default=QuestionFormat.TEXT
    )
    connected_surveys = models.ManyToManyField(Survey, related_name="questions")
    question_type = models.CharField(
        max_length=15, choices=QuestionType.choices, default=QuestionType.ONETIME
    )
    answers = OneToManyManager["Answer"]

    # Relationships to parent classes
    survey_template = models.ManyToManyField(SurveyTemplate, related_name="questions", through="QuestionOrder")
    bank_question = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="question_bank", null=True
    )

    # All questions tyoe possible
    slider_question = models.OneToOneField(
        SliderQuestion, on_delete=models.CASCADE, null=True, blank=True
    )
    multiple_choice_question = models.OneToOneField(
        MultipleChoiceQuestion, on_delete=models.CASCADE, null=True, blank=True
    )
    yes_no_question = models.OneToOneField(
        YesNoQuestion, on_delete=models.CASCADE, null=True, blank=True
    )
    text_question = models.OneToOneField(
        TextQuestion, on_delete=models.CASCADE, null=True, blank=True
    )

    def clone_for_survey(self, survey: Survey) -> "Question":
        """
        Make a deep‐copy of this Question for a new Survey, including
        M2M links and any OneToOne “child” models.
        """
        # Wrap in a transaction so partial copies get rolled back on error
        with transaction.atomic():
            # Copy all field values except pk
            data = {
                f.name: getattr(self, f.name)
                for f in self._meta.fields
                if f.name not in ('id', 'pk')
            }
            # Remove any fields referring to child OneToOne we will handle those separately
            for rel_name in (
                'slider_question',
                'multiple_choice_question',
                'yes_no_question',
                'text_question',
            ):
                data.pop(rel_name, None)

            # Add link to question bank
            data['bank_question'] = data.get('bank_question') 

            # Create the new Question, pointing at the new survey 
            new_q = Question.objects.create(**data)
            # Add link to survey:
            new_q.connected_surveys.set([survey])

            # Copy each OneToOne “child” model if present:
            one_to_one_fields = {
                'slider_question': SliderQuestion,
                'multiple_choice_question': MultipleChoiceQuestion,
                'yes_no_question': YesNoQuestion,
                'text_question': TextQuestion,
            }
            for field_name, model_cls in one_to_one_fields.items():
                child = getattr(self, field_name, None)
                if child is not None:
                    # Build child data dict
                    child_data = {
                        f.name: getattr(child, f.name)
                        for f in child._meta.fields
                        if f.name not in ('id', 'pk', field_name) 
                    }
                    # Set the back‐reference to new_q
                    child_data[field_name.replace('_question','')] = new_q
                    # Create the cloned child
                    model_cls.objects.create(**child_data)

            return new_q

    @property
    def specific_question(self) -> BaseQuestionDetails | None:
        """
        This method is a getter function for this question specific question (type).
        The @property decorator makes it possible to call this
        method without ().

        Args:
            self.question_format (QuestionFormat): The question format of this question

        Returns:
            BaseQuestionDetails or None: Returns a specific question if it exists, otherwise None
        """
        if self.question_format == QuestionFormat.TEXT:
            return cast(TextQuestion, self.text_question)
        elif self.question_format == QuestionFormat.MULTIPLE_CHOICE:
            return cast(MultipleChoiceQuestion, self.multiple_choice_question)
        elif self.question_format == QuestionFormat.YES_NO:
            return cast(YesNoQuestion, self.yes_no_question)
        elif self.question_format == QuestionFormat.SLIDER:
            return cast(SliderQuestion, self.slider_question)

        logger.warning(
            "No specific question could be found. This suggests the question was initialized wrong!"
        )
        return None

    def __str__(self) -> str:
        return f"{self.question_format} ({self.question})"


# What this model does needs to be explained here
class Answer(models.Model):
    is_answered = models.BooleanField(default=False)  # pyright: ignore
    survey = models.ForeignKey(
        SurveyUserResult, on_delete=models.CASCADE, related_name="answers", null=True
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers", null=True
    )
    comment = models.CharField(max_length=255, null=True, blank=True)
    free_text_answer = models.CharField(max_length=255, null=True, blank=True)
    multiple_choice_answer = models.JSONField(
        default=list, null=True, blank=True
    )  # Stores a list of booleans
    yes_no_answer = models.BooleanField(null=True, blank=True)  # pyright: ignore
    slider_answer = models.FloatField(null=True, blank=True)

    @property
    def answer(self):
        if self.question:
            if self.question.question_format == QuestionFormat.MULTIPLE_CHOICE:
                return self.multiple_choice_answer
            elif self.question.question_format == QuestionFormat.YES_NO:
                return self.yes_no_answer
            elif self.question.question_format == QuestionFormat.TEXT:
                return self.free_text_answer
            elif self.question.question_format == QuestionFormat.SLIDER:
                return self.slider_answer

        return None

    @property
    def answer_format(self) -> QuestionFormat | None:
        """
        This method is a getter function for the answer format.
        The @property decorator makes it possible to call this
        method without ().

        Args:
            self.question (Question): The question this answer relates to

        Returns:
            QuestionFormat or None: Returns a QuestionFormat if question exists, otherwise None
        """
        if self.question is not None:
            # This looks kinda shady but it is necessary for the typing
            # The Django model fields ensures that question and question.question_format
            # will be of correct type, but to handle the edgecase where
            # question is None and lsp type errors we need to cast
            return cast(QuestionFormat, cast(Question, self.question).question_format)

        logger.warning(
            "Answer format returned None. This suggests that no related question exists!"
        )
        return None

    def __str__(self) -> str:
        return f"{self.survey} ({self.is_answered})"


class EmailList(models.Model):
    email = models.EmailField(unique=True)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="org_emails",
        null=True,
        blank=True,
    )
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name="group")
    objects: models.Manager

    def __str__(self) -> str:
        return f"{self.email}"


class QuestionOrder(models.Model):
    survey_temp   = models.ForeignKey(SurveyTemplate, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("survey_temp", "question"),)
        ordering = ("order",)
    
    def __str__(self) -> str:
        return f"{self.order}. {self.question}"
