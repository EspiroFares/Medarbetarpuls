from django.db import models
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import all classes and such here to be able to type class-fields
    from django.db.models import CharField


class Organization(models.Model):
    name: "CharField" = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.name}"
