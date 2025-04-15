from getpass import getuser
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.manager import BaseManager
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
import logging
import math
from typing import cast
import time
from .models import *


class DiagramType(models.TextChoices):
    BAR = "bar", "Bar"
    PIE = "pie", "Pie"
    LINE = "line", "Line"
    STACK = "stack", "Stack"


class AnalysisHandler:
    """
    Handles logic for survey analysis.
    """

    def get_survey(self, survey_name: str) -> Survey:
        """Retrieve a survey by its name."""
        return Survey.objects.get(name=survey_name)

    def get_survey_result(self, survey):
        """Retrieve a specific SurveyUserResult."""
        return SurveyUserResult.objects.filter(published_survey=survey)

    def get_question(self, question_txt: str) -> Question:
        """Fetch the question object by text. Assumes there is only one question phrased the same way."""
        # Right now the question is fetched by an exact match,
        # use question__icontains= instead of question= for a more flexible match.
        return Question.objects.filter(question__icontains=question_txt).first()

    def get_answers(
        self,
        question: Question,
        survey: Survey | None = None,
    ):
        """Get answers for a given question, optionally filtered to a specific survey/result."""

        filters = {"question": question, "is_answered": True}

        if survey:
            results = self.get_survey_result(survey)
            filters["survey__in"] = results

        return Answer.objects.filter(**filters)

    # --------- SLIDER-QUESTION FUNCTIONALITY -------------
    def calculate_enps_data(self, answers) -> tuple[int, int, int]:
        """Categorize responses into promoters, passives, and detractors."""

        promoters = answers.filter(slider_answer__gte=9).count()
        passives = answers.filter(slider_answer__gte=7, slider_answer__lt=9).count()
        detractors = answers.filter(slider_answer__lt=7).count()
        return promoters, passives, detractors

    def calculate_enps_score(
        self, promoters: int, passives: int, detractors: int
    ) -> int:
        # Compute eNPS score.
        total = promoters + passives + detractors
        return (
            math.floor(((promoters - detractors) / total) * 100) if total > 0 else 0
        )  # if statement needed because we can get zero division error otherwise

    def get_response_distribution_slider(self, answers) -> list[int]:
        """Count how many respondents picked each value (1-10)."""
        return [answers.filter(slider_answer=i).count() for i in range(1, 11)]

    def get_enps_summary(
        self,
        survey_name: str,
    ):
        """
        Get all data needed to render ENPS analysis:
        standard deviation, variation coefficient, score, labels, data distribution, raw responses.

        With survey_id set to None you get all the answers from an eNPS question.
        """
        survey = self.get_survey(survey_name)
        question_txt = (
            "How likely are you to recommend this company as a place to work?"
        )
        question = self.get_question(question_txt)
        print(question)
        answers = self.get_answers(question, survey)
        # answers = self.get_answers(question)
        promoters, passives, detractors = self.calculate_enps_data(answers)
        print(promoters, passives, detractors)
        score = self.calculate_enps_score(promoters, passives, detractors)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        return {
            "score": score,
            "labels": ["Promoters", "Passives", "Detractors"],
            "data": [promoters, passives, detractors],
            "slider_values": list(range(1, 11)),
            "distribution": distribution,
            "standard_deviation": standard_deviation,
            "variation_coefficient": variation_coefficient,
        }

    def calculate_mean(self, answers) -> float:
        "Calculates mean for slider answers."
        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        n = len(values)
        if n == 0:
            return 0.0
        mean = sum(values) / n
        return mean

    def calculate_standard_deviation(self, answers) -> float:
        """Calculate standard deviation for slider answers."""
        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        n = len(values)
        if n == 0:
            return 0.0
        mean = self.calculate_mean(answers)
        variance = sum((x - mean) ** 2 for x in values) / n
        standard_deviation = math.sqrt(variance)
        return standard_deviation

    def calculate_variation_coefficient(self, answers) -> float:
        """Calculate coefficient of variation for slider answers."""

        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        n = len(values)
        if n == 0:
            return 0.0
        mean = self.calculate_mean(answers)
        if mean == 0:
            return 0.0
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)
        cv = (std_dev / mean) * 100
        return round(cv, 2)

    def get_slider_summary(
        self,
        question_txt: str,
        survey_name: str,
    ):
        """
        Get all data needed to render slider analysis:
        standard deviation, variation coefficient, data distribution, raw responses.

        With survey_id set to None you get all the answers from the question.
        """
        survey = self.get_survey(survey_name)
        question = self.get_question(question_txt)
        answers = self.get_answers(question, survey)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        return {
            "slider_values": list(range(1, 11)),
            "distribution": distribution,
            "standard_deviation": standard_deviation,
            "variation_coefficient": variation_coefficient,
        }

    # ---------------- MULTIPLE CHOICE ------------
    def get_response_distribution_mc(self, answers, answer_options) -> list[int]:
        """Count how many respondents picked each answer."""
        # this function is a little weird because of the structure of the answers (list with booleans) and the structure of the answer options (list with strings)
        # it looks at all occurences of true at the corresponding index to answer option

        dist = [0] * len(answer_options)
        print("HEJ: ", dist)

        for a in answers:
            selected_options = a.multiple_choice_answer
            if selected_options:
                for idx, selected in enumerate(selected_options):
                    if selected and idx < len(dist):
                        dist[idx] += 1
        return dist

    def get_multiple_choice_summary(
        self,
        question_txt: str,
        survey_name: str,
    ):
        survey = self.get_survey(survey_name)
        question = self.get_question(question_txt)
        answer_options = question.specific_question.options
        answers = self.get_answers(question, survey)
        distribution = self.get_response_distribution_mc(answers, answer_options)
        print(answers.filter(multiple_choice_answer="A").count())
        print(distribution)
        return {
            "question": question_txt,
            "answer_options": answer_options,
            "distribution": distribution,
        }

    # ----------- YES NO --------------------
    def get_response_distribution_yes_no(self, answers) -> list[int]:
        """Count how many respondents picked each answer."""

        yes_count = sum(1 for a in answers if a.yes_no_answer is True)
        print(yes_count)
        no_count = sum(1 for a in answers if a.yes_no_answer is False)
        return [no_count, yes_count]

    def get_yes_no_summary(
        self,
        question_txt: str,
        survey_name: str,
    ):
        survey = self.get_survey(survey_name)
        question = self.get_question(question_txt)
        answer_options = [
            "YES",
            "NO",
        ]
        answers = self.get_answers(question, survey)
        distribution = self.get_response_distribution_yes_no(answers)
        return {
            "question": question,
            "answer_options": answer_options,
            "distribution": distribution,
        }

    # ----------------------- HISTORY ----------------------

    # def enps_history_distribution(self,
    # start

    # )
