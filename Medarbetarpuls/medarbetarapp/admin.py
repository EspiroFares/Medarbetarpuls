from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
<<<<<<< HEAD
from .models import CustomUser  # Import your CustomUser model
=======
from .models import CustomUser, Organization  # Import your CustomUser model
>>>>>>> origin/dev


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        "email",
        "name",
        "user_role",
        "is_staff",
        "is_superuser",
    )  # Customize displayed fields
    search_fields = ("email", "name")  # Add search functionality
    list_filter = ("user_role", "is_staff", "is_superuser")  # Add filters
    ordering = ("email",)  # Default sorting order
    fieldsets = (
        (None, {"fields": ("email", "password")}),
<<<<<<< HEAD
        ("Personal Info", {"fields": ("name", "role")}),
=======
        ("Personal Info", {"fields": ("name", "user_role")}),
>>>>>>> origin/dev
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
<<<<<<< HEAD
                    "role",
=======
                    "user_role",
>>>>>>> origin/dev
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
<<<<<<< HEAD
=======

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "get_admins", "get_employee_groups", "get_question_bank", "get_survey_templates", "get_org_emails")
    search_fields = ("name",)

    @admin.display(description="Admins")
    def get_admins(self, obj):
        return ", ".join([admin.email for admin in obj.admins.all()])

    @admin.display(description="Employee Group")
    def get_employee_groups(self, obj):
        return ", ".join([group.name for group in obj.employee_groups.all()])

    @admin.display(description="Question Bank")
    def get_question_bank(self, obj):
        return ", ".join([question.question for question in obj.question_bank.all()])

    @admin.display(description="Survey Templates")
    def get_survey_templates(self, obj):
        return ", ".join([template.name for template in obj.survey_template_bank.all()])

    @admin.display(description="Organization Emails")
    def get_org_emails(self, obj): 
        return ", ".join([template.email for template in obj.org_emails.all()])
>>>>>>> origin/dev
