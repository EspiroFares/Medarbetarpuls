# medarbetarapp/migrations/0027_remove_survey_template_m2m.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('medarbetarapp', '0026_auto_20250424_0705'),
    ]
    operations = [
        migrations.RemoveField(
            model_name='question',
            name='survey_template',
        ),
    ]
