from . import models

STANDARD_QUESTIONS = [
    ["ENPS: Rekommendera Arbetsgivare","Hur sannolikt är det att du skulle rekommendera din arbetsgivare till andra?", models.QuestionFormat.SLIDER, models.QuestionType.ENPS, [1, 10]],
    ["Nuvarande arbetsroll", "Vad är din nuvarande arbetsroll?", models.QuestionFormat.TEXT, models.QuestionType.BUILTIN],
    ["Nuvarande arbetsbelastning", "Hur nöjd är du med din nuvarande arbetsbelastning?", models.QuestionFormat.SLIDER, models.QuestionType.BUILTIN, [1, 10]],
    ["Feedback på arbete", "Hur ofta får du feedback på ditt arbete?", models.QuestionFormat.MULTIPLE_CHOICE, models.QuestionType.BUILTIN, ["Aldrig", "Sällan", "Ibland", "Ofta", "Alltid"]],
    ["Största utmaningar i arbetet","Vad är din största utmaning i ditt arbete?", models.QuestionFormat.TEXT, models.QuestionType.BUILTIN],
]