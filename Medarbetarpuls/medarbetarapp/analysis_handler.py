import math
import logging
from django.db import models
from django.db.models import QuerySet
from typing import Any, Dict, List, Union, Optional
from .models import (
    Survey,
    SurveyUserResult,
    Question,
    Answer,
    EmployeeGroup,
    CustomUser,
    QuestionFormat,
    QuestionType,
    Organization,
)
from statistics import median

logger = logging.getLogger(__name__)


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
        """
        Retrieve a specific survey by its ID.

        Args:
            survey_id (int): The ID of the survey to retrieve.

        Returns:
            Survey: The Survey instance matching the given ID."""
        return Survey.objects.get(id=survey_id)

    def get_survey_result(self, survey: Survey) -> QuerySet[SurveyUserResult]:
        """
        Retrieve all user results associated with a given survey.

        Args:
            survey (Survey): The survey instance for which to fetch results.

        Returns:
            QuerySet[SurveyUserResult]: A queryset of SurveyUserResult objects
            filtered by the provided survey.
        """
        return SurveyUserResult.objects.filter(published_survey=survey)

    def get_question(self, question_id: int) -> Optional[Question]:
        """
        Retrieve a question by its ID, returning the first match or None.

        Args:
            question_id (int): The ID of the question to retrieve.

        Returns:
            Optional[Question]: The Question instance if found; otherwise, None.
        """
        # Right now the question is fetched by an exact match,
        # use question__icontains= instead of question= for a more flexible match.
        return Question.objects.filter(id=question_id).first()

    def get_surveys_for_group(self, employee_group: EmployeeGroup) -> QuerySet[Survey]:
        """
        Retrieve all unique surveys associated with a specific employee group.

        Args:
            employee_group (EmployeeGroup): The employee group for which to fetch surveys.

        Returns:
            QuerySet[Survey]: A distinct queryset of Survey objects linked to the given group.
        """
        return (
            Survey.objects.filter(employee_groups=employee_group)
            .order_by("-sending_date")
            .distinct()
        )

    def get_answers(
        self,
        question: Question,
        survey: Survey | None = None,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> QuerySet[Answer]:
        """
        Retrieve answered responses for a given question, optionally filtered by survey, user, or employee group.

        Args:
            question (Question): The question for which to fetch answers.
            survey (Survey, optional): Limit answers to those from this survey.
            user (CustomUser, optional): Limit answers to those submitted by this user.
            employee_group (EmployeeGroup, optional): Limit answers to those from members of this group.

        Returns:
            QuerySet[Answer]: A queryset of Answer objects matching the provided filters, or an empty queryset if none found.
        """
        filters = {"question": question, "is_answered": True}
        if survey:
            results = SurveyUserResult.objects.filter(published_survey=survey)
            filters["survey__in"] = results
        if user:
            filters["survey__user"] = user

        elif employee_group:
            filters["survey__user__in"] = employee_group.employees.all()

        answers = Answer.objects.filter(**filters)

        if not answers.exists():
            if user:
                logger.info(
                    "No answers available for %s", user or survey or employee_group
                )
                return Answer.objects.none()
            logger.info("No answers available.")
            return Answer.objects.none()
        return answers

    def get_comments(
        self,
        question: Question,
        survey: Survey | None = None,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> QuerySet[Answer]:
        """
        Retrieve all non-empty comments for a given question, optionally filtered by survey, user, or employee group.

        Args:
            question (Question): The question for which to fetch comments.
            survey (Survey, optional): Limit comments to those from this survey.
            user (CustomUser, optional): Limit comments to those submitted by this user.
            employee_group (EmployeeGroup, optional): Limit comments to those from members of this group.

        Returns:
            QuerySet[Answer]: A queryset of Answer objects with non-empty comments matching the provided filters.
        """
        filters = {"question": question, "is_answered": True, "comment__isnull": False}

        if survey:
            results = self.get_survey_result(survey)
            filters["survey__in"] = results

        if user:
            filters["survey__user"] = user

        elif employee_group:
            filters["survey__user__in"] = employee_group.employees.all()

        return Answer.objects.filter(**filters).exclude(
            comment=""
        )  # only returns comments non empty comments, do we want empty comments?

    def get_text_comments(self, answers: QuerySet):
        """
        Returns list of comment text from the given Answer-Queryset

        Args:
            comment (Queryset of Answer): The Queryset that will give the comment-text list

        Returns:
            List[CharField]: A list of the comment texts.
        """
        text_comments = []
        for answer in answers:
            text_comments.append(answer.comment)
        return text_comments

    def get_participation_metrics(
        self, surveys: List[Survey], employee_group: EmployeeGroup
    ) -> Dict[str, list]:
        """
        Calculate participation metrics for a given survey and employee group.

        Args:
            survey (Survey): The survey for which to compute metrics.
            employee_group (EmployeeGroup): The group of employees whose participation is measured.

        Returns:
            Dict[str, float]: A dictionary containing:
            participant_count (float): Total number of employees in the group.
            answered_count (float): Number of users in the group who have answered the survey.
            answer_pct (float): Percentage of participants who answered (rounded to 1 decimal).
        """
        result = {
            "survey_sending_dates": [],
            "participant_count_list": [],
            "answered_count_list": [],
            "answer_pct_list": [],
        }
        for survey in surveys:
            total_participants = employee_group.employees.count()
            answered_count = SurveyUserResult.objects.filter(
                published_survey=survey,
                user__in=employee_group.employees.all(),
                is_answered=True,
            ).count()
            answer_pct = round((answered_count / total_participants) * 100, 1)
            result["survey_sending_dates"].append(
                survey.sending_date.strftime("%Y-%m-%d")
            )
            result["participant_count_list"].append(total_participants)
            result["answered_count_list"].append(answered_count)
            result["answer_pct_list"].append(answer_pct)

        return result

    def get_respondents(
        self, survey: Survey, employee_group: EmployeeGroup | None = None
    ):
        filters = {"published_survey": survey}  # add is answered here?

        if employee_group:
            filters["user__in"] = employee_group.employees.all()

        users = list(
            CustomUser.objects.filter(
                survey_results__in=SurveyUserResult.objects.filter(**filters)
            ).distinct()
        )
        anonymous_users = {f"User {i}": users[i] for i in range(len(users))}
        return anonymous_users

    def get_bank_questions(self, surveys: list | None = None):
        """
        Returns all questions that are part of an organization's question bank.
        """
        bank_questions = []
        if surveys:
            all_survey_questions = []
            for survey in surveys:
                all_survey_questions += survey.questions.all()

            # Filter bank questions that are used in the surveys
            filtered_bank_questions = [
                question
                for question in all_survey_questions
                if question.bank_question_tag is not None
            ]

            # This part of the code makes sure we only get singular bank_question objects
            seen_questions = []
            for question in filtered_bank_questions:
                if question.question not in seen_questions:
                    bank_questions.append(question)
                    seen_questions.append(question.question)
        else:
            bank_questions = Question.objects.filter(
                bank_question__isnull=False,
            ).distinct()

        # Remove free text questions since it's not possible to analyze them
        for idx, question in enumerate(bank_questions):
            if question.question_format == QuestionFormat.TEXT:
                bank_questions.pop(idx)
        return bank_questions

    # --------- SLIDER-QUESTION FUNCTIONALITY -------------
    def calculate_enps_data(self, answers) -> tuple[int, int, int]:
        """
        Calculate the counts of promoters, passives, and detractors from slider answers.

        Args:
            answers (QuerySet[Answer]): A queryset of Answer objects with a `slider_answer` field.

        Returns:
            tuple[int, int, int]:
            promoters (int): Number of answers with slider_answer >= 9.
            passives (int): Number of answers with 7 <= slider_answer < 9.
            detractors (int): Number of answers with slider_answer < 7.
        """
        promoters = answers.filter(slider_answer__gte=9).count()
        passives = answers.filter(slider_answer__gte=7, slider_answer__lt=9).count()
        detractors = answers.filter(slider_answer__lt=7).count()
        return promoters, passives, detractors

    def calculate_enps_score(
        self, promoters: int, passives: int, detractors: int
    ) -> int:
        """
        Calculate the employee Net Promoter Score (eNPS) as an integer percentage.

        Args:
            promoters (int): Number of promoter responses.
            passives (int): Number of passive responses.
            detractors (int): Number of detractor responses.

        Returns:
            int: eNPS score computed as floor((promoters – detractors) / total * 100),
            or 0 if there are no responses.
        """
        # Compute eNPS score.
        total = promoters + passives + detractors
        return (
            math.floor(((promoters - detractors) / total) * 100) if total > 0 else 0
        )  # if statement needed because we can get zero division error otherwise

    def get_response_distribution_slider(self, answers) -> list[int]:
        """
        Retrieve the distribution of slider responses for values 1 through 10.

        Args:
            answers (QuerySet[Answer]): A queryset of Answer objects containing a `slider_answer` field.

        Returns:
            list[int]: A list of 10 integers where the element at index i-1 is the count of responses with `slider_answer == i` for i from 1 to 10.
        """
        return [
            answers.filter(
                slider_answer__gte=i - 0.5, slider_answer__lt=i + 0.5
            ).count()
            for i in range(1, 11)
        ]

    def get_enps_summary(
        self,
        survey: Survey,
        question: Question,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> Dict[str, Any]:
        """
        Get all data needed to render ENPS analysis:
        standard deviation, variation coefficient, score, labels, data distribution, raw responses.

        With survey_id set to None you get all the answers from an eNPS question.
        """
        answers = self.get_answers(
            question, survey, user=user, employee_group=employee_group
        )
        print("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
        print("BBBBBBBBBBB", answers)

        # answers = self.get_answers(question)
        promoters, passives, detractors = self.calculate_enps_data(answers)
        score = self.calculate_enps_score(promoters, passives, detractors)
        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        comments = self.get_comments(
            question, survey, user=user, employee_group=employee_group
        )
        return {
            "question": question,
            "question_format": question.question_type,
            "answers": answers,
            "enpsScore": score,
            "comments": comments,
            "text_comments": self.get_text_comments(comments),
            "enpsPieLabels": ["Detractors", "Passives", "Promoters"],
            "enpsPieData": [detractors, passives, promoters],
            "slider_values": [str(i) for i in range(1, 11)],
            "enpsDistribution": distribution,
            "standard_deviation": standard_deviation,
            "variation_coefficient": variation_coefficient,
        }

    def calculate_mean(self, answers) -> float:
        """
        Calculate the average slider answer from a set of responses.

        Args:
            answers (QuerySet[Answer] or Iterable[Answer]): A collection of Answer objects
            with a `slider_answer` attribute.

        Returns:
            float: The mean of all non-null `slider_answer` values, or 0.0 if there are none.
        """
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
        return round(standard_deviation, 2)

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

    def calculate_median(self, answers) -> float:
        """Calculate median for slider answers."""
        values = [a.slider_answer for a in answers if a.slider_answer is not None]
        if not values:
            return 0.0
        return round(median(values), 2)

    def get_slider_summary(
        self,
        question: Question,
        survey: Survey,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> Dict[str, Any]:
        """
        Get all data needed to render slider analysis:
        standard deviation, variation coefficient, data distribution, raw responses.

        With survey_id set to None you get all the answers from the question.
        """

        answers = self.get_answers(
            question, survey, user=user, employee_group=employee_group
        )

        distribution = self.get_response_distribution_slider(answers)
        standard_deviation = self.calculate_standard_deviation(answers)
        variation_coefficient = self.calculate_variation_coefficient(answers)
        median = self.calculate_median(answers)

        comments = self.get_comments(
            question, survey, user=user, employee_group=employee_group
        )
        mean = round(self.calculate_mean(answers), 2)
        return {
            "question": question,
            "question_format": question.question_format,
            "answers": answers,
            "slider_values": [str(i) for i in range(1, 11)],
            "comments": comments,
            "text_comments": self.get_text_comments(comments),
            "slider_distribution": distribution,
            "slider_std": standard_deviation,
            "slider_cv": variation_coefficient,
            "slider_mean": mean,
            "slider_median": median,
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
        question: Question,
        survey: Survey,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> Dict[str, Any]:
        if not question or not question.specific_question:
            # Om question eller specific_question inte finns
            return {
                "question": question,
                "question_format": question.question_format,
                "answers": [],
                "comments": [],
                "text_comments": [],
                "multiple_choice_labels": [],
                "distribution": [],
            }

        answer_options = question.specific_question.options
        answers = self.get_answers(
            question, survey, user=user, employee_group=employee_group
        )

        distribution = self.get_response_distribution_mc(answers, answer_options)
        comments = self.get_comments(question, survey)
        return {
            "question": question,
            "question_format": question.question_format,
            "answers": answers,
            "comments": comments,
            "text_comments": self.get_text_comments(comments),
            "multiple_choice_labels": answer_options,
            "multiple_choice_distribution": distribution,
        }

    # ----------- YES NO --------------------
    def get_response_distribution_yes_no(self, answers) -> list[int]:
        """Count how many respondents picked each answer."""

        yes_count = sum(1 for a in answers if a.yes_no_answer is True)
        no_count = sum(1 for a in answers if a.yes_no_answer is False)
        return [yes_count, no_count]

    def get_yes_no_summary(
        self,
        question: Question,
        survey: Survey,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> Dict[str, Any]:
        answer_options = [
            "YES",
            "NO",
        ]
        answers = self.get_answers(
            question, survey, user=user, employee_group=employee_group
        )
        distribution = self.get_response_distribution_yes_no(answers)
        answer_count = answers.count()

        yes_percentage = (
            round((distribution[0] / answer_count) * 100, 1) if answers else 0
        )
        no_percentage = (
            round((distribution[1] / answer_count) * 100, 1) if answers else 0
        )

        comments = self.get_comments(question, survey)
        return {
            "question": question,
            "question_format": question.question_format,
            "comments": comments,
            "answers": answers,
            "text_comments": self.get_text_comments(comments),
            "yes_no_labels": answer_options,
            "yes_no_distribution": distribution,
            "yes_percentage": yes_percentage,
            "no_percentage": no_percentage,
        }

    # ---------------- FREE TEXT -------------
    def get_free_text_summary(
        self,
        question: Question,
        survey: Survey,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> Dict[str, Any]:
        answers = self.get_answers(
            question, survey, user=user, employee_group=employee_group
        )

        text_answers = []
        for answer in answers:
            text_answers.append(answer.free_text_answer)

        comments = self.get_comments(question, survey)
        answer_count = answers.count() if answers else 0

        return {
            "question": question,
            "question_format": question.question_format,
            "answers": answers,
            "free_text_answers": text_answers,
            "answer_count": answer_count,
            "comments": comments,
            "text_comments": self.get_text_comments(comments),
        }

    # --------------- FULL SURVEY SUMMARY -----------

    def get_survey_summary(
        self,
        survey_id: int,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> Dict[str, Any]:
        """
        This function returns a summary for a whole survey. Optionally filtered to a specific user or an employee_group.
        """
        survey = Survey.objects.filter(id=survey_id).first()

        summary = {
            "survey": survey,
            "user": user,
            "employee_group": employee_group,
            "summaries": [],
        }

        questions = Question.objects.filter(connected_surveys__id=survey_id)

        for question in questions:
            if question.question_format == QuestionFormat.MULTIPLE_CHOICE:
                question_summary = self.get_multiple_choice_summary(
                    question=question,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            elif question.question_format == QuestionFormat.YES_NO:
                question_summary = self.get_yes_no_summary(
                    question=question,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            elif question.question_format == QuestionFormat.TEXT:
                question_summary = self.get_free_text_summary(
                    question=question,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            elif question.question_type == QuestionType.ENPS:
                question_summary = self.get_enps_summary(
                    survey=survey,
                    question=question,
                    user=user,
                    employee_group=employee_group,
                )
            elif question.question_format == QuestionFormat.SLIDER:
                question_summary = self.get_slider_summary(
                    question=question,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            else:
                continue  # skip unknown formats

            summary["summaries"].append(question_summary)

        return summary

    # ----------------------- HISTORY ----------------------

    def get_filtered_surveys(
        self,
        start: str,
        end: str,
        employee_group: EmployeeGroup | None = None,
    ):
        """
        Returns a list of surveys within the timespan start, end. Optionally filtered to a specific employeegroup.
        """
        surveys = Survey.objects.all()
        surveys = surveys.filter(deadline__gte=start)
        surveys = surveys.filter(deadline__lte=end)

        if employee_group:
            surveys = surveys.filter(employee_groups=employee_group)

        return surveys.order_by("deadline")

    def get_question_trend(
        self,
        question: Question,
        surveys: list[Survey],
        employee_group: EmployeeGroup | None = None,
        user: CustomUser | None = None,
    ):
        """
        Returns a trend over time for a single question across multiple surveys.

        """
        trend_summary = {
            "survey_ids_trend": [],
            "sending_dates_trend": [],
        }

        for survey in sorted(surveys, key=lambda s: s.sending_date, reverse=True):
            _question = question

            question_obj = survey.questions.filter(
                question=_question.question
            ).first()  # fetch the question object corresponding to the same string as the input question
            if question_obj is None:
                continue

            if question_obj.question_format == QuestionFormat.MULTIPLE_CHOICE:
                question_summary = self.get_multiple_choice_summary(
                    question=question_obj,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )

            elif question_obj.question_format == QuestionFormat.YES_NO:
                question_summary = self.get_yes_no_summary(
                    question=question_obj,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            elif question_obj.question_format == QuestionFormat.TEXT:
                question_summary = self.get_free_text_summary(
                    question=question_obj,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            elif question_obj.question_type == QuestionType.ENPS:
                question_summary = self.get_enps_summary(
                    question=question_obj,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            elif question_obj.question_format == QuestionFormat.SLIDER:
                question_summary = self.get_slider_summary(
                    question=question_obj,
                    survey=survey,
                    user=user,
                    employee_group=employee_group,
                )
            else:
                continue
            trend_summary["survey_ids_trend"].append(survey.id)
            trend_summary["sending_dates_trend"].append(
                survey.sending_date.strftime("%Y-%m-%d")
            )

            for key, value in question_summary.items():
                key = f"{key}_trend"
                if key not in trend_summary:
                    trend_summary[key] = []
                trend_summary[key].append(value)

        return trend_summary

    def get_survey_answer_distribution(
        self,
        survey: Survey,
        user: CustomUser | None = None,
        employee_group: EmployeeGroup | None = None,
    ) -> dict[str, Any]:
        result = {
            "questions": [],
            "answered_counts": [],
            "total_participants": [],
        }
        total_participants = survey.survey_results.count()

        for q in survey.questions.all().order_by("id"):
            answers_qs = self.get_answers(
                question=q,
                survey=survey,
                user=user,
                employee_group=employee_group,
            )

            result["questions"].append(q)
            result["answered_counts"].append(answers_qs.count())
            result["total_participants"].append(total_participants)

        return result
