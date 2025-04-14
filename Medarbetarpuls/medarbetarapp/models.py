from getpass import getuser
from importlib.metadata import distribution
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.manager import BaseManager
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
import logging
import math
from typing import cast


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
    is_viewable = models.BooleanField(default=False)  # pyright: ignore

    def __str__(self) -> str:
        return f"{self.name} ({self.creator})"


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
    survey_template = models.ManyToManyField(SurveyTemplate, related_name="questions")
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
        return f"{self.question_format} ({self.question_type})"


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
    yes_no_answer = models.BooleanField(default=False, null=True, blank=True)  # pyright: ignore
    slider_answer = models.FloatField(null=True, blank=True)

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


class DiagramType(models.TextChoices):
    BAR = "bar", "Bar"
    PIE = "pie", "Pie"
    LINE = "line", "Line"
    STACK = "stack", "Stack"


class AnalysisHandler:
    """
    Handles logic for survey analysis.
    """

    def get_survey(self, survey_id: int) -> Survey:
        """Retrieve a survey by its ID."""
        return Survey.objects.get(id=survey_id)

    def get_survey_result(self, survey_id: int):
        """Retrieve a specific SurveyUserResult."""
        return SurveyUserResult.objects.filter(published_survey__id=survey_id)

    def get_question(self, question_txt: str) -> Question:
        """Fetch the question object by text. Assumes there is only one question phrased the same way."""
        # Right now the question is fetched by an exact match,
        # use question__icontains= instead of question= for a more flexible match.
        return Question.objects.filter(question__icontains=question_txt).first()

    def get_answers(
        self,
        question: Question,
        survey_id: int | None = None,
    ):
        """Get answers for a given question, optionally filtered to a specific survey/result."""

        filters = {"question": question, "is_answered": True}

        if survey_id:
            results = self.get_survey_result(survey_id)
            filters["survey__in"] = results

        return Answer.objects.filter(**filters)

    # --------- SLIDER-QUESTION FUNCTIONALITY -------------
    def calculate_enps_data(self, answers) -> tuple[int, int, int]:
        """Categorize responses into promoters, passives, and detractors."""

        promoters = answers.filter(slider_answer__gte=9).count()
        passives = answers.filter(slider_answer__gte=7, slider_answer__lt=9).count()
        detractors = answers.filter(slider_answer__lt=7).count()
        return promoters, passives, detractors

    def calculate_enps_score(
        self, promoters: int, passives: int, detractors: int
    ) -> int:
        # Compute eNPS score.
        total = promoters + passives + detractors
        return (
            math.floor(((promoters - detractors) / total) * 100) if total > 0 else 0
        )  # if statement needed because we can get zero division error otherwise

    def get_response_distribution_slider(self, answers) -> list[int]:
        """Count how many respondents picked each value (1-10)."""
        return [answers.filter(slider_answer=i).count() for i in range(1, 11)]

    def get_enps_summary(
        self,
        survey_id: int | None = None,
    ):
        """
        Get all data needed to render ENPS analysis:
        standard deviation, variation coefficient, score, labels, data distribution, raw responses.

        With survey_id set to None you get all the answers from an eNPS question.
        """
        question_txt = (
            "How likely are you to recommend this company as a place to work?"
        )
        question = self.get_question(question_txt)
        print(question)
        answers = self.get_answers(question, survey_id)
        # answers = self.get_answers(question)
        promoters, passives, detractors = self.calculate_enps_data(answers)
        print(promoters, passives, detractors)
        score = self.calculate_enps_score(promoters, passives, detractors)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        return {
            "score": score,
            "labels": ["Promoters", "Passives", "Detractors"],
            "data": [promoters, passives, detractors],
            "slider_values": list(range(1, 11)),
            "distribution": distribution,
            "standard_deviation": standard_deviation,
            "variation_coefficient": variation_coefficient,
        }

    def calculate_mean(self, answers) -> float:
        "Calculates mean for slider answers."
        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        n = len(values)
        if n == 0:
            return 0.0
        mean = sum(values) / n
        return mean

    def calculate_standard_deviation(self, answers) -> float:
        """Calculate standard deviation for slider answers."""
        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        n = len(values)
        if n == 0:
            return 0.0
        mean = sum(values) / n  # maybe change this for the calculate_mean function?
        variance = sum((x - mean) ** 2 for x in values) / n
        standard_deviation = math.sqrt(variance)
        return standard_deviation

    def calculate_variation_coefficient(self, answers) -> float:
        """Calculate coefficient of variation for slider answers."""
        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        n = len(values)
        if n == 0:
            return 0.0
        mean = sum(values) / n  # maybe change this for the calculate_mean function?
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)
        cv = (std_dev / mean) * 100
        return round(cv, 2)

    def get_slider_summary(
        self,
        question_txt: str,
        survey_id: int | None = None,
    ):
        """
        Get all data needed to render slider analysis:
        standard deviation, variation coefficient, data distribution, raw responses.

        With survey_id set to None you get all the answers from the question.
        """
        question = self.get_question(question_txt)
        answers = self.get_answers(question, survey_id)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        return {
            "slider_values": list(range(1, 11)),
            "distribution": distribution,
            "standard_deviation": standard_deviation,
            "variation_coefficient": variation_coefficient,
        }

    # ---------------- MULTIPLE CHOICE ------------
    def get_response_distribution_mc(self, answers, answer_options) -> list[int]:
        """Count how many respondents picked each answer."""
        # this function is a little weird because of the structure of the answers (list with booleans) and the structure of the answer options (list with strings)
        # it looks at all occurences of true at the corresponding index to answer option

        dist = [0] * len(answer_options)
        print("HEJ: ", dist)

        for a in answers:
            selected_options = a.multiple_choice_answer
            if selected_options:
                for idx, selected in enumerate(selected_options):
                    if selected and idx < len(dist):
                        dist[idx] += 1
        return dist

    def get_multiple_choice_summary(
        self,
        question_txt: str,
        survey_id: int | None = None,
    ):
        question = self.get_question(question_txt)
        answer_options = question.specific_question.options
        answers = self.get_answers(question, survey_id)
        distribution = self.get_response_distribution_mc(answers, answer_options)
        print(answers.filter(multiple_choice_answer="A").count())
        print(distribution)
        return {
            "question": question,
            "answer_options": answer_options,
            "distribution": distribution,
        }

    # ----------- YES NO --------------------
    def get_yes_no_summary(
        self,
        question_txt: str,
        survey_id: int | None = None,
    ):
        question = self.get_question(question_txt)
        answer_options = question.specific_question.options
        answers = self.get_answers(question, survey_id)
        # distribution =

        return {}


class EmailList(models.Model):
    email = models.EmailField(unique=True)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="org_emails",
        null=True,
        blank=True,
    )
    objects: models.Manager

    def __str__(self) -> str:
        return f"{self.email}"
