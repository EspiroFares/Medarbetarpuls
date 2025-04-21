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

    def get_survey(self, survey_id: int) -> Survey:
        """Retrieve a survey by its id."""
        return Survey.objects.get(id=survey_id)

    def get_survey_result(self, survey):
        """Retrieve a specific SurveyUserResult."""
        return SurveyUserResult.objects.filter(published_survey=survey)

    def get_question(self, question_id: int) -> Question:
        """Fetch the question object by text. Assumes there is only one question phrased the same way."""
        # Right now the question is fetched by an exact match,
        # use question__icontains= instead of question= for a more flexible match.
        return Question.objects.filter(id=question_id).first()

    def get_answers(
        self,
        question: Question,
        survey: Survey | None = None,
        user: CustomUser | None = None,
    ):
        """Get answers for a given question. Can optionally be filtered to a specific survey/result or a specific user/responder."""
        filters = {"question": question, "is_answered": True}

        if survey:
            results = self.get_survey_result(survey)
            filters["survey__in"] = results

        if user:
            if user == survey.creator:
                print("No answers available for the creator of the survey.")
                return None

            filters["survey__user"] = user

        answers = Answer.objects.filter(**filters)

        if not answers.exists():
            if user:
                print(f"No answers available for {user}.")
                return None
            print("No answers available.")
            return None

        return answers

    def get_comments(
        self,
        question: Question,
        survey: Survey | None = None,
    ):
        """Returns all comments from a question, optionaly question and survey."""
        filters = {"question": question, "is_answered": True, "comment__isnull": False}

        if survey:
            results = self.get_survey_result(survey)
            filters["survey__in"] = results

        return Answer.objects.filter(**filters).exclude(
            comment=""
        )  # only returns comments non empty comments, do we want empty comments?

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
        survey_id: int,
        user: CustomUser | None = None,
    ):
        """
        Get all data needed to render ENPS analysis:
        standard deviation, variation coefficient, score, labels, data distribution, raw responses.

        With survey_id set to None you get all the answers from an eNPS question.
        """
        survey = self.get_survey(survey_id)
        question_txt = (
            "How likely are you to recommend this company as a place to work?"
        )
        question = Question.objects.filter(question__icontains=question_txt).first()
        answers = self.get_answers(question, survey, user)
        # answers = self.get_answers(question)
        promoters, passives, detractors = self.calculate_enps_data(answers)
        score = self.calculate_enps_score(promoters, passives, detractors)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        comments = self.get_comments(question, survey)
        return {
            "score": score,
            "comments": comments,
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
        question_id: int,
        survey_id: int,
        user: CustomUser | None = None,
    ):
        """
        Get all data needed to render slider analysis:
        standard deviation, variation coefficient, data distribution, raw responses.

        With survey_id set to None you get all the answers from the question.
        """
        survey = self.get_survey(survey_id)
        question = self.get_question(question_id)
        answers = self.get_answers(question, survey, user)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        comments = self.get_comments(question, survey)
        return {
            "question": question,
            "answers": answers,
            "slider_values": list(range(1, 11)),
            "comments": comments,
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

        for a in answers:
            selected_options = a.multiple_choice_answer
            if selected_options:
                for idx, selected in enumerate(selected_options):
                    if selected and idx < len(dist):
                        dist[idx] += 1
        return dist

    def get_multiple_choice_summary(
        self,
        question_id: int,
        survey_id: int,
        user: CustomUser | None = None,
    ):
        survey = self.get_survey(survey_id)
        question = self.get_question(question_id)
        answer_options = question.specific_question.options
        answers = self.get_answers(question, survey, user)
        distribution = self.get_response_distribution_mc(answers, answer_options)
        comments = self.get_comments(question, survey)
        return {
            "question": question,
            "answers": answers,
            "comments": comments,
            "answer_options": answer_options,
            "distribution": distribution,
        }

    # ----------- YES NO --------------------
    def get_response_distribution_yes_no(self, answers) -> list[int]:
        """Count how many respondents picked each answer."""

        yes_count = sum(1 for a in answers if a.yes_no_answer is True)
        no_count = sum(1 for a in answers if a.yes_no_answer is False)
        return [no_count, yes_count]

    def get_yes_no_summary(
        self,
        question_id: int,
        survey_id: int,
        user: CustomUser | None = None,
    ):
        survey = self.get_survey(survey_id)
        question = self.get_question(question_id)
        answer_options = [
            "YES",
            "NO",
        ]
        answers = self.get_answers(question, survey, user)
        distribution = self.get_response_distribution_yes_no(answers)
        comments = self.get_comments(question, survey)
        return {
            "question": question,
            "answers": answers,
            "comments": comments,
            "answer_options": answer_options,
            "distribution": distribution,
        }

    # ---------------- FREE TEXT -------------
    def get_free_text_summary(
        self,
        question_id: int,
        survey_id: int,
        user: CustomUser | None = None,
    ):
        survey = self.get_survey(survey_id)
        question = self.get_question(question_id)
        answers = self.get_answers(question, survey, user)
        comments = self.get_comments(question, survey)
        filters = {
            "question": question,
            "is_answered": True,
        }
        answer_count = Answer.objects.filter(**filters).count()

        return {
            "question": question,
            "answers": answers,
            "answer_count": answer_count,
            "comments": comments,
        }

    # --------------- FULL SURVEY SUMMARY -----------
    def get_survey_summary(
        self,
        survey_id: int,
        user: CustomUser | None = None,
    ):
        """
        This function returns a summary for a whole survey. Optionally filtered to a specific user.
        """
        survey = Survey.objects.filter(id=survey_id).first()

        summary = {
            "Survey": survey,
            "Summaries": [],
        }
        questions = Question.objects.filter(connected_surveys__id=survey_id)

        for question in questions:
            if question.question_format == QuestionFormat.MULTIPLE_CHOICE:
                question_summary = self.get_multiple_choice_summary(
                    question.id, survey.id
                )
            elif question.question_format == QuestionFormat.YES_NO:
                question_summary = self.get_yes_no_summary(question.id, survey.id)
            elif question.question_format == QuestionFormat.TEXT:
                question_summary = self.get_free_text_summary(question.id, survey.id)
            elif question.question_format == QuestionFormat.SLIDER:
                question_summary = self.get_slider_summary(question.id, survey.id)
            elif question.question_type == QuestionType.ENPS:
                question_summary = self.get_enps_summary(survey.id)

            summary["Summaries"].append(question_summary)

        return summary

    # ----------------------- HISTORY ----------------------

    def enps_history_distribution(self):
        # TO DO: Add time filters
        # TO DO: add employeegroup option
        question_txt = (
            "How likely are you to recommend this company as a place to work?"
        )

        question = Question.objects.filter(question__icontains=question_txt).first()
        surveys = Survey.objects.order_by("sending_date")
        history = []

        for s in surveys:
            answers = self.get_answers(question, s)
            promoters, passives, detractors = self.calculate_enps_data(answers)
            score = self.calculate_enps_score(promoters, passives, detractors)
            history.append(
                {
                    "survey_id": s.id,
                    "deadline": s.deadline.strftime("%Y-%m-%d"),
                    "score": score,
                }
            )
        # survey_ids = [item["survey_id"] for item in history]
        enps_scores = [item["score"] for item in history]
        survey_deadlines = [item["deadline"] for item in history]

        return {
            "deadlines": survey_deadlines,
            "scores": enps_scores,
        }
