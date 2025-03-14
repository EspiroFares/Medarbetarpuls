from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db.models.query import QuerySet
from typing import TYPE_CHECKING
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Import all classes and such here to be able to type class-fields
    from django.db.models import CharField
    from django.db.models import IntegerField
    from django.db.models import EmailField
    from django.db.models import ForeignKey
    from django.db.models import BooleanField


class Organization(models.Model):
    name: "CharField" = models.CharField(max_length=255)

    # Add an explicit type hint for employeeGroups (this is just for readability)
    employeeGroups: QuerySet["EmployeeGroup"]

    def __str__(self) -> str:
        return f"{self.name}"


class EmployeeGroup(models.Model):
    name: "CharField" = models.CharField(max_length=255)
    organization: "ForeignKey" = models.ForeignKey(
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
    def create_user(self, email, name, password=None, **extra_fields):
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
    email: "EmailField" = models.EmailField(unique=True)
    name: "CharField" = models.CharField(max_length=255)
    role: "CharField" = models.CharField(
        max_length=15, choices=UserRole.choices, default=UserRole.SURVEY_RESPONDER
    )

    is_staff: "BooleanField" = models.BooleanField(
        default=False  # pyright: ignore
    )  # Allows access to admin panel
    is_superuser: "BooleanField" = models.BooleanField(
        default=False  # pyright: ignore
    )  # Allows you to do something in the admin panel
    is_active: "BooleanField" = models.BooleanField(
        default=True  # pyright: ignore
    )  # Controls if the user can log in

    objects = CustomUserManager()

    USERNAME_FIELD = "email"  # Use email instead of username when searching through db

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"
