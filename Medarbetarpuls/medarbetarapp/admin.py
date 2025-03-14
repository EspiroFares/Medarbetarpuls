from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser  # Import your CustomUser model


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        "email",
        "name",
        "role",
        "is_staff",
        "is_superuser",
    )  # Customize displayed fields
    search_fields = ("email", "name")  # Add search functionality
    list_filter = ("role", "is_staff", "is_superuser")  # Add filters
    ordering = ("email",)  # Default sorting order
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "role",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


# Register the CustomUser model
admin.site.register(CustomUser, CustomUserAdmin)
