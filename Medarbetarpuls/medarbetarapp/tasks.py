from celery import shared_task
from django.utils import timezone
from django.utils.timezone import make_aware
from datetime import timedelta, datetime, time
from django.core.mail import send_mail


@shared_task
def publish_survey_async(survey_id: int):
    """
    This function can be used to schedule publishing 
    of survey with id survey_id.  
    """
    from .models import Survey  # Avoid circular import

    survey: Survey = Survey.objects.get(id=survey_id)
    survey.publish_survey()


@shared_task
def send_notifications(survey_id: int):
    """
    This function can be used when scheduling dynamic 
    notifications for survey with id survey_id. Will 
    only notify users who have not answered survey.
    """
    from .models import Survey  # Avoid circular import
    seen_employees = set()

    # Get users who need to be notified
    survey: Survey = Survey.objects.get(id=survey_id)

    for group in survey.employee_groups.all():
        for employee in group.employees.all():
            if employee.id not in seen_employees and not result_in_survey(employee, survey_id):
                seen_employees.add(employee)

    # Update with new last_notification time
    survey.last_notification = timezone.now() 
    survey.save()

    # Send email to notify
    send_mail(
        subject="Påminnelse",
        message="Det finns en enkät att svara på i Medarbetarpuls",
        from_email="medarbetarpuls@gmail.com",
        recipient_list=[employee.email for employee in seen_employees],
        fail_silently=False,
    )


def schedule_notification(survey_id: int, reminders: list[str]):
    """
    This function can be used to schedule when 
    notifications should be sent for survey with id 
    survey_id. Notifications will be scheduled accordning 
    to days in reminders list.
    """
    for reminder in reminders: 
        # Target day = today + reminder days
        target_date = timezone.now().date() + timedelta(days=int(reminder))

        # Set desired time of arrival on the day
        target_datetime = datetime.combine(target_date, time(hour=8, minute=0))

        # Make timezone-aware
        target_eta = make_aware(target_datetime)

        # Onetime notification to be sent in reminder days
        send_notifications.apply_async(
            args=[survey_id],
            eta=target_eta
        )


def result_in_survey(employee, survey_id: int) -> bool: 
    """
    Returns if an employee has answered the survey 
    with id survey_id. 
    """
    for result in employee.survey_results.all(): 
        survey = result.published_survey 
        if survey.id == survey_id: 
            return result.is_answered  

    return False
