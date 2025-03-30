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
    employeeGroups: BaseManager

    def __str__(self) -> str:
        return f"{self.name}"


class EmployeeGroup(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="employeeGroups"
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
            logger.error("The emial field must be set")
            raise ValueError("The email field must be set")
        if not name:
            logger.error("The name field must be set")
            raise ValueError("The name field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


# The actual custom user class
class CustomUser(AbstractBaseUser, PermissionsMixin):  # pyright: ignore
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    id = models.IntegerField(unique=True)
    userRole = models.CharField(
        max_length=15, choices=UserRole.choices, default=UserRole.SURVEY_RESPONDER
    )
    authorizationLevel = models.IntegerField(default=0)  # pyright: ignore

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
