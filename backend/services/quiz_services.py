# app/services/quiz_service.py
from models import db, Quiz, Question, Choice, UserProgress, Module
from services.core_services import PointsService
from datetime import datetime

class QuizService:
    #Handles quiz grading, scoring, and user progress updates.

    @staticmethod
    def evaluate_quiz(user, quiz_id, user_answers):

        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            raise ValueError("Quiz not found.")

        total_questions = quiz.questions.count()
        correct_answers = 0

        for question in quiz.questions:
            chosen_choice_id = user_answers.get(str(question.id)) or user_answers.get(question.id)
            if not chosen_choice_id:
                continue  # No answer provided

            selected_choice = Choice.query.get(chosen_choice_id)
            if selected_choice and selected_choice.is_correct:
                correct_answers += 1

        # Calculate score
        score_percent = int((correct_answers / total_questions) * 100)
        passed = score_percent >= quiz.passing_score

        module = quiz.module
        progress = UserProgress.query.filter_by(user_id=user.id, module_id=module.id).first()
        if not progress:
            progress = UserProgress(user_id=user.id, module_id=module.id)

        progress.last_score = score_percent
        progress.completion_percent = 100 if passed else 50  # Example rule
        if passed:
            progress.completed_at = datetime.utcnow()

        db.session.add(progress)
        db.session.commit()

        # Award points if passed
        if passed:
            PointsService.award_points(user, "complete_quiz", metadata=f"Quiz {quiz.title}")

        return {
            "quiz_id": quiz.id,
            "score_percent": score_percent,
            "passed": passed,
            "total_questions": total_questions,
            "correct_answers": correct_answers
        }
