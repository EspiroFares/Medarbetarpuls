from django.db import models
from django.db.models.query import QuerySet
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import all classes and such here to be able to type class-fields
    from django.db.models import CharField
    from django.db.models import IntegerField
    from django.db.models import ForeignKey


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
