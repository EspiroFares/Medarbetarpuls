from django.db import models
from django.db.models.manager import BaseManager
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
import logging


logger = logging.getLogger(__name__)


class Organization(models.Model):
    name = models.CharField(max_length=255)
    # Add an explicit type hint for employeeGroups (this is just for readability)
    employee_groups: BaseManager
    admins: BaseManager

    def __str__(self) -> str:
        return f"{self.name}"


class EmployeeGroup(models.Model):
    name = models.CharField(max_length=255)
    # Add an explicit type hint for employees (this is just for readability)
    employees: BaseManager
    # Add an explicit type hint for managers (this is just for readability)
    managers: BaseManager
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employee_groups", null=True
    )
    published_surveys: BaseManager
    survey_templates: BaseManager

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
            logger.error("The emial field must be set")
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
    managed_groups = models.ManyToManyField(EmployeeGroup, related_name="managers")
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



# Below are models for surveys and their results


# What this model does needs to be explained here
class Survey(models.Model):
    name = models.CharField(max_length=255)  # Do we want names for surveys???
    creator = models.OneToOneField(CustomUser, on_delete=models.CASCADE) 
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name="published_surveys")
    survey_results: BaseManager
    deadline = models.DateTimeField()  # stores both date and time (e.g., YYYY-MM-DD HH:MM:SS)
    sending_date = models.DateTimeField()  # stores both date and time (e.g., YYYY-MM-DD HH:MM:SS)
    # What is this???
    collected_answer_count = models.IntegerField(default=0)  # pyright: ignore 
    is_viewable = models.BooleanField(default=False)  # pyright: ignore
    
    def __str__(self) -> str:
        return f"{self.name} ({self.creator})"


# What this model does needs to be explained here
class SurveyTemplate(models.Model): 
    name = models.CharField(max_length=255)  # Do we want names for surveyTemplates???
    creator = models.OneToOneField(CustomUser, on_delete=models.CASCADE) 
    employee_groups = models.ManyToManyField(EmployeeGroup, related_name="survey_templates")
    last_edited = models.DateTimeField()  # stores both date and time (e.g., YYYY-MM-DD HH:MM:SS)

    def __str__(self) -> str:
        return f"{self.name} ({self.creator})"


# What this model does needs to be explained here
class SurveyResult(models.Model):
    published_survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="survey_results", null=True
    )
    user_id = models.IntegerField()
    answers: BaseManager
    is_answered = models.BooleanField(default=False)  # pyright: ignore

    def __str__(self) -> str:
        return f"{self.user_id} ({self.is_answered})"


# What this model does needs to be explained here
class Answer(models.Model):
    is_answered = models.BooleanField(default=False)  # pyright: ignore
    survey = models.ForeignKey(
        SurveyResult, on_delete=models.CASCADE, related_name="answers", null=True
    )
    comment = models.CharField(max_length=255)
    free_text_answer = models.CharField(max_length=255) 
    multiple_choice_answer = models.JSONField(default=list)  # Stores a list of booleans
    yes_no_answer = models.BooleanField(default=False)  # pyright: ignore
    slider_answer = models.FloatField()
    
    def __str__(self) -> str:
        return f"{self.survey} ({self.is_answered})"
