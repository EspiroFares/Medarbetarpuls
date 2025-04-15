from celery import shared_task

@shared_task
def publish_survey_async(survey_id: int):
    from .models import Survey  # Avoid circular import

    survey: Survey = Survey.objects.get(id=survey_id)
    survey.publish_survey()
