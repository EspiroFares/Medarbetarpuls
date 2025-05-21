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


class AnalysisHandler:
    """
    Handles logic for survey analysis.
    """

    def get_survey(self, survey_id: int) -> Survey:
        """
        Retrieve a specific survey by its ID.
        """
        return Survey.objects.get(id=survey_id)

    def get_survey_result(self, survey: Survey) -> QuerySet[SurveyUserResult]:
        """
        Retrieve all the results from users associated with a given survey.

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
        """
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

        return Answer.objects.filter(**filters).exclude(comment="")

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
        Calculate participation metrics across a list of surveys for a specific employee group.

        Args:
            surveys (List[Survey]): A list of surveys to calculate metrics for.
            employee_group (EmployeeGroup): The group of employees whose participation is measured.

        Returns:
            Dict[str, list]: A dictionary containing:
                - 'survey_sending_dates' (List[str]): Formatted sending dates for each survey.
                - 'participant_count_list' (List[int]): Total number of participants in the group per survey.
                - 'answered_count_list' (List[int]): Number of respondents who answered per survey.
                - 'answer_pct_list' (List[float]): Percentage of respondents who answered, per survey.
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
        """
        Retrieves a dictionary of anonymous labels mapped to users who answered the given survey.

        Args:
            survey (Survey): The survey for which to retrieve respondents.
            employee_group (EmployeeGroup, optional): If provided, limit respondents to members of this group.

        Returns:
            Dict[str, CustomUser]: Anonymous labels mapping 'User 0', 'User 1', etc. to their corresponding responder,

        """
        filters = {"published_survey": survey}

        if employee_group:
            filters["user__in"] = employee_group.employees.all()

        # Retrieve a list of user objects that responded to the given survey
        users = list(
            CustomUser.objects.filter(
                survey_results__in=SurveyUserResult.objects.filter(**filters)
            ).distinct()
        )

        # Map the users to an id
        anonymous_users = {f"User {i}": users[i] for i in range(len(users))}
        return anonymous_users

    def get_bank_questions(self, surveys: list | None = None):
        """
        Retrieves all available bank questions or all bank questions that have been given across a list of surveys.

        Args:
            surveys (list | None): A list of Survey objects to filter questions from. If None, fetch from the full question bank.

        Returns:
            List[Question]: A list of unique, non-text bank questions.

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
        Generate a summary of eNPS analysis.

        Args:
            survey (Survey): The survey instance containing the question.
            question (Question): The ENPS-type question to analyze.
            user (CustomUser, optional): Filter responses to a specific user.
            employee_group (EmployeeGroup, optional): Filter responses to a specific group.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'question': The question object.
                - 'question_format': The question's type (eNPS).
                - 'answers': QuerySet of relevant answers.
                - 'enpsScore': The computed eNPS score.
                - 'comments': QuerySet of Answer objects with comments.
                - 'text_comments': List of comment strings.
                - 'enpsPieLabels': Category labels for pie chart.
                - 'enpsPieData': Counts for each ENPS category.
                - 'slider_values': Slider labels (1–10).
                - 'enpsDistribution': List of counts per slider value.
                - 'standard_deviation': Standard deviation of answers.
                - 'variation_coefficient': Coefficient of variation.
        """

        answers = self.get_answers(
            question, survey, user=user, employee_group=employee_group
        )

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
            Generates a summary for slider analysis.

            Includes response distribution, mean, median, standard deviation, coefficient of variation,
            and associated comments. Filters can be applied to a specific user or employee group.

        Args:
            question (Question): The slider-format question to analyze.
            survey (Survey): The survey containing the question.
            user (CustomUser, optional): Filter answers to a specific user.
            employee_group (EmployeeGroup, optional): Filter answers to a specific group.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'question': The question object.
                - 'question_format': The question format (slider).
                - 'answers': QuerySet of relevant answers.
                - 'slider_values': List of slider labels (1–10).
                - 'comments': QuerySet of Answer objects with comments.
                - 'text_comments': List of extracted comment strings.
                - 'slider_distribution': List of counts per slider value.
                - 'slider_std': Standard deviation of slider answers.
                - 'slider_cv': Coefficient of variation.
                - 'slider_mean': Mean slider score.
                - 'slider_median': Median slider score.

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
        """Count how many respondents selected each option in a multiple-choice question.

        Args:
            answers (QuerySet[Answer]): A collection of Answer objects with multiple_choice_answer fields.
            answer_options (List[str]): The list of answer options for the question (Ex. 'A', 'B', 'C').

        Returns:
            List[int]: Distribution over the answers, where each index corresponds to the number of times that option was selected.

        """
        dist = [0] * len(answer_options)

        for a in answers:
            selected_options = a.multiple_choice_answer
            if selected_options:
                # Loop over the available options and check if the option is selected. If it's selected (set to True) add +1 to the corresponding index of that answer option.
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
        """
        Generate a summary for a multiple choice question.

        This includes answer distribution, option labels, and associated comments.
        Optionally filters responses by user or employee group.

        Args:
            question (Question): The multiple-choice question to summarize.
            survey (Survey): The survey the question belongs to.
            user (CustomUser, optional): Limit responses to a specific user.
            employee_group (EmployeeGroup, optional): Limit responses to users in this group.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'question': The question object.
                - 'question_format': Format type (multiple choice).
                - 'answers': QuerySet of relevant answers.
                - 'comments': QuerySet of answers with comments.
                - 'text_comments': List of comment strings.
                - 'multiple_choice_labels': List of answer options.
                - 'multiple_choice_distribution': Count of selections per option.

        """
        if not question or not question.specific_question:
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
        """Retrieves the distribution for how many respondents picked each answer."""

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
        """
        Generate a summary for a yes_no question.

        Includes distribution counts, percentage breakdown, and associated comments.
        Filters can be applied for a specific user or employee group.

        Args:
            question (Question): The yes/no question to analyze.
            survey (Survey): The survey containing the question.
            user (CustomUser, optional): Filter responses by a specific user.
            employee_group (EmployeeGroup, optional): Filter responses by a group.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'question': The question object.
                - 'question_format': The format of the question (yes/no).
                - 'answers': QuerySet of relevant answers.
                - 'comments': QuerySet of answers with non-empty comments.
                - 'text_comments': List of extracted comment strings.
                - 'yes_no_labels': ['YES', 'NO'] labels.
                - 'yes_no_distribution': Count of Yes/No responses.
                - 'yes_percentage': Percentage of Yes responses.
                - 'no_percentage': Percentage of No responses.
        """
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
        """
        Generate a summary for a free text question

        Extracts all text answers, counts total responses, and gathers associated comments.
        Filters can be applied for a specific user or employee group.

        Args:
            question (Question): The free-text question to analyze.
            survey (Survey): The survey containing the question.
            user (CustomUser, optional): Filter responses by a specific user.
            employee_group (EmployeeGroup, optional): Filter responses by a group.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'question': The question object.
                - 'question_format': The question format (text).
                - 'answers': QuerySet of relevant Answer objects.
                - 'free_text_answers': List of raw text answers.
                - 'answer_count': Total number of responses.
                - 'comments': QuerySet of answers with comments.
                - 'text_comments': List of comment strings.


        """
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

        Args:
            survey_id (int): The ID of the survey to summarize.
            user (CustomUser, optional): Filter responses to a specific user.
            employee_group (EmployeeGroup, optional): Filter responses to users in this group.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'survey': The Survey object.
                - 'user': The user that the summaries were filtered to.
                - 'employee_group': The group that the summaries were filtered to.
                - 'summaries': List of per-question summary dictionaries.
        """
        survey = Survey.objects.filter(id=survey_id).first()

        summary = {
            "survey": survey,
            "user": user,
            "employee_group": employee_group,
            "summaries": [],
        }
        # Fetch all questions from the given survey_id
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
    def get_question_trend(
        self,
        question: Question,
        surveys: list[Survey],
        employee_group: EmployeeGroup | None = None,
        user: CustomUser | None = None,
    ):
        """
        Generate a trend summary for a specific question across multiple surveys.

        For each survey where the question is present, this method collects summary statistics (depending on the question format) and organizes them chronologically by survey sending date (Ex. the surveys go from [latest, ..., oldest]).

         Args:
            question (Question): The question to track over time.
            surveys (list[Survey]): A list of surveys to evaluate.
            employee_group (EmployeeGroup, optional): Filter answers by group membership.
            user (CustomUser, optional): Filter answers by user.

        Returns:
            Dict[str, Any]: A dictionary with trend data including:
                - 'survey_ids_trend': List of survey IDs (in reverse chronological order).
                - 'sending_dates_trend': Corresponding survey sending dates (formatted) (in chronological order).
                - '{key}_trend': A trend list for each metric in the individual question summaries.
        """
        trend_summary = {
            "survey_ids_trend": [],
            "sending_dates_trend": [],
        }

        for survey in sorted(surveys, key=lambda s: s.sending_date, reverse=True):
            _question = question

            # Fetch the question object corresponding to the same string as the input question. This is needed because each survey has unique question objects.
            question_obj = survey.questions.filter(question=_question.question).first()
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
        """
        Compute how many participants answered each question in a survey.

        Optionally filters the answers by user or employee group. Returns the answer count
        per question, as well as the total number of survey participants.

        Args:
            survey (Survey): The survey whose questions will be analyzed.
            user (CustomUser, optional): Limit answer counts to this user.
            employee_group (EmployeeGroup, optional): Limit answer counts to users in this group.

        Returns:
            dict[str, Any]: A dictionary with:
                - 'questions': List of Question objects in order.
                - 'answered_counts': Number of answers received per question.
                - 'total_participants': Total participant count for each question.
        """
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
