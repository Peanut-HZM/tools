"""
OpenSpec 课程服务层
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.openspec_course import (
    OpenSpecCourseChapter,
    OpenSpecCourseQuiz,
    OpenSpecCourseQuizQuestion,
    OpenSpecCourseQuizOption,
    UserCourseProgress,
    OpenSpecCourseResource,
)
from app.schemas.openspec_course import (
    ChapterCreate,
    ChapterUpdate,
    ChapterReorderRequest,
    QuizCreate,
    QuizUpdate,
    QuizSubmitRequest,
    QuizResult,
    UserProgressCreate,
    UserProgressUpdate,
    ResourceCreate,
    ResourceUpdate,
)

logger = logging.getLogger(__name__)


class OpenSpecCourseService:
    """OpenSpec 课程服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============ 章节管理 ============

    def get_chapters(self) -> List[OpenSpecCourseChapter]:
        """获取所有章节"""
        return self.db.query(OpenSpecCourseChapter).order_by(OpenSpecCourseChapter.order).all()

    def get_chapter_by_id(self, chapter_id: int) -> Optional[OpenSpecCourseChapter]:
        """根据 ID 获取章节"""
        return self.db.query(OpenSpecCourseChapter).filter(OpenSpecCourseChapter.id == chapter_id).first()

    def get_chapter_by_slug(self, slug: str) -> Optional[OpenSpecCourseChapter]:
        """根据 slug 获取章节"""
        return self.db.query(OpenSpecCourseChapter).filter(OpenSpecCourseChapter.slug == slug).first()

    def create_chapter(self, chapter: ChapterCreate) -> OpenSpecCourseChapter:
        """创建章节"""
        db_chapter = OpenSpecCourseChapter(**chapter.model_dump())
        self.db.add(db_chapter)
        self.db.commit()
        self.db.refresh(db_chapter)
        logger.info(f"创建章节：{db_chapter.slug}")
        return db_chapter

    def update_chapter(self, chapter_id: int, chapter: ChapterUpdate) -> Optional[OpenSpecCourseChapter]:
        """更新章节"""
        db_chapter = self.get_chapter_by_id(chapter_id)
        if not db_chapter:
            return None

        update_data = chapter.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_chapter, field, value)

        self.db.commit()
        self.db.refresh(db_chapter)
        logger.info(f"更新章节：{chapter_id}")
        return db_chapter

    def delete_chapter(self, chapter_id: int) -> bool:
        """删除章节"""
        db_chapter = self.get_chapter_by_id(chapter_id)
        if not db_chapter:
            return False

        self.db.delete(db_chapter)
        self.db.commit()
        logger.info(f"删除章节：{chapter_id}")
        return True

    def reorder_chapters(self, reorder_request: ChapterReorderRequest) -> bool:
        """批量更新章节顺序"""
        try:
            for chapter_data in reorder_request.chapters:
                chapter_id = chapter_data.get("id")
                new_order = chapter_data.get("order")

                if chapter_id is None or new_order is None:
                    continue

                db_chapter = self.get_chapter_by_id(chapter_id)
                if db_chapter:
                    db_chapter.order = new_order

            self.db.commit()
            logger.info(f"批量更新章节顺序：{len(reorder_request.chapters)} 个章节")
            return True
        except Exception as e:
            logger.error(f"批量更新章节顺序失败：{e}")
            self.db.rollback()
            return False

    # ============ 测验管理 ============

    def get_quiz_by_chapter_id(self, chapter_id: int) -> Optional[OpenSpecCourseQuiz]:
        """根据章节 ID 获取测验"""
        return self.db.query(OpenSpecCourseQuiz).filter(OpenSpecCourseQuiz.chapter_id == chapter_id).first()

    def get_quiz_by_id(self, quiz_id: int) -> Optional[OpenSpecCourseQuiz]:
        """根据 ID 获取测验"""
        return self.db.query(OpenSpecCourseQuiz).filter(OpenSpecCourseQuiz.id == quiz_id).first()

    def get_quiz_questions(self, quiz_id: int):
        """获取测验的所有问题"""
        from app.models.openspec_course import OpenSpecCourseQuizQuestion, OpenSpecCourseQuizOption
        questions = self.db.query(OpenSpecCourseQuizQuestion).filter(
            OpenSpecCourseQuizQuestion.quiz_id == quiz_id
        ).order_by(OpenSpecCourseQuizQuestion.order).all()

        result = []
        for q in questions:
            options = self.db.query(OpenSpecCourseQuizOption).filter(
                OpenSpecCourseQuizOption.question_id == q.id
            ).all()
            result.append({
                "id": q.id,
                "quiz_id": q.quiz_id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "order": q.order,
                "created_at": q.created_at,
                "options": [{
                    "id": opt.id,
                    "question_id": opt.question_id,
                    "option_text": opt.option_text,
                    "option_index": opt.option_index,
                    "created_at": opt.created_at,
                } for opt in options],
            })
        return result

    def create_quiz(self, quiz: QuizCreate) -> OpenSpecCourseQuiz:
        """创建测验"""
        db_quiz = OpenSpecCourseQuiz(
            chapter_id=quiz.chapter_id,
            title=quiz.title,
            passing_score=quiz.passing_score,
        )
        self.db.add(db_quiz)
        self.db.flush()  # 获取 quiz ID

        # 创建问题和选项
        for q_idx, question in enumerate(quiz.questions):
            db_question = OpenSpecCourseQuizQuestion(
                quiz_id=db_quiz.id,
                question_text=question.question_text,
                question_type=question.question_type,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
                order=q_idx,
            )
            self.db.add(db_question)
            self.db.flush()

            # 创建选项
            for option in question.options:
                db_option = OpenSpecCourseQuizOption(
                    question_id=db_question.id,
                    option_text=option.option_text,
                    option_index=option.option_index,
                )
                self.db.add(db_option)

        self.db.commit()
        self.db.refresh(db_quiz)
        logger.info(f"创建测验：{quiz.title}")
        return db_quiz

    def update_quiz(self, quiz_id: int, quiz: QuizUpdate) -> Optional[OpenSpecCourseQuiz]:
        """更新测验"""
        db_quiz = self.get_quiz_by_id(quiz_id)
        if not db_quiz:
            return None

        update_data = quiz.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_quiz, field, value)

        self.db.commit()
        self.db.refresh(db_quiz)
        return db_quiz

    def delete_quiz(self, quiz_id: int) -> bool:
        """删除测验"""
        db_quiz = self.get_quiz_by_id(quiz_id)
        if not db_quiz:
            return False

        self.db.delete(db_quiz)
        self.db.commit()
        return True

    def submit_quiz(self, quiz_id: int, user_id: str, answers: Dict[int, List[int]]) -> QuizResult:
        """提交测验并返回结果"""
        db_quiz = self.get_quiz_by_id(quiz_id)
        if not db_quiz:
            raise ValueError(f"Quiz {quiz_id} not found")

        # 获取所有问题
        questions = self.db.query(OpenSpecCourseQuizQuestion).filter(
            OpenSpecCourseQuizQuestion.quiz_id == quiz_id
        ).all()

        total_questions = len(questions)
        correct_count = 0
        details = []

        for question in questions:
            correct_answer = [int(x) for x in question.correct_answer.split(",")]
            user_answer = answers.get(question.id, [])

            is_correct = set(user_answer) == set(correct_answer)
            if is_correct:
                correct_count += 1

            # 获取选项文本
            options = self.db.query(OpenSpecCourseQuizOption).filter(
                OpenSpecCourseQuizOption.question_id == question.id
            ).all()
            option_texts = {opt.option_index: opt.option_text for opt in options}

            details.append({
                "question_id": question.id,
                "question_text": question.question_text,
                "correct_answer": correct_answer,
                "user_answer": user_answer,
                "is_correct": is_correct,
                "explanation": question.explanation,
                "correct_option_texts": [option_texts.get(i) for i in correct_answer],
                "user_option_texts": [option_texts.get(i) for i in user_answer],
            })

        score = (correct_count / total_questions * 100) if total_questions > 0 else 0
        passed = score >= db_quiz.passing_score

        # 更新用户进度
        progress = self.get_user_progress(user_id, db_quiz.chapter_id)
        if progress:
            progress.quiz_score = score
            progress.quiz_passed = passed
            if passed:
                progress.status = "completed"
                progress.completed_at = datetime.now()
            else:
                progress.status = "in_progress"
            self.db.commit()
        else:
            # 如果用户没有进度记录，创建一个新的
            from app.models.openspec_course import UserCourseProgress
            new_progress = UserCourseProgress(
                user_id=user_id,
                chapter_id=db_quiz.chapter_id,
                status="completed" if passed else "in_progress",
                quiz_score=score,
                quiz_passed=passed,
                video_progress=0,
                completed_at=datetime.now() if passed else None,
            )
            self.db.add(new_progress)
            self.db.commit()

        return QuizResult(
            quiz_id=quiz_id,
            total_questions=total_questions,
            correct_count=correct_count,
            score=score,
            passed=passed,
            details=details,
        )

    # ============ 进度管理 ============

    def get_user_progress(self, user_id: str, chapter_id: int) -> Optional[UserCourseProgress]:
        """获取用户进度"""
        return self.db.query(UserCourseProgress).filter(
            and_(
                UserCourseProgress.user_id == user_id,
                UserCourseProgress.chapter_id == chapter_id
            )
        ).first()

    def get_all_user_progress(self, user_id: str) -> List[UserCourseProgress]:
        """获取用户所有进度"""
        return self.db.query(UserCourseProgress).filter(
            UserCourseProgress.user_id == user_id
        ).all()

    def create_or_update_progress(self, user_id: str, chapter_id: int, progress: UserProgressUpdate) -> UserCourseProgress:
        """创建或更新用户进度"""
        db_progress = self.get_user_progress(user_id, chapter_id)

        if db_progress:
            # 更新
            update_data = progress.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_progress, field, value)
        else:
            # 创建
            db_progress = UserCourseProgress(
                user_id=user_id,
                chapter_id=chapter_id,
                status=progress.status or "not_started",
                quiz_score=progress.quiz_score,
                quiz_passed=progress.quiz_passed or False,
                video_progress=progress.video_progress or 0,
            )
            self.db.add(db_progress)

        self.db.commit()
        self.db.refresh(db_progress)
        return db_progress

    def get_course_progress_summary(self, user_id: str) -> Dict[str, Any]:
        """获取课程进度汇总"""
        all_chapters = self.get_chapters()
        user_progress = self.get_all_user_progress(user_id)

        # 创建章节 ID 到进度的映射
        progress_map = {p.chapter_id: p for p in user_progress}

        # 为没有进度的章节创建默认进度（手动构建 dict 以回避 Schema 验证问题）
        chapters_with_progress = []
        for chapter in all_chapters:
            if chapter.id in progress_map:
                p = progress_map[chapter.id]
                chapters_with_progress.append({
                    "id": p.id,
                    "user_id": p.user_id,
                    "chapter_id": p.chapter_id,
                    "status": p.status,
                    "quiz_score": p.quiz_score,
                    "quiz_passed": p.quiz_passed or False,
                    "video_progress": p.video_progress or 0,
                    "completed_at": p.completed_at,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                })
            else:
                # 创建默认进度数据
                chapters_with_progress.append({
                    "id": 0,
                    "user_id": user_id,
                    "chapter_id": chapter.id,
                    "status": "not_started",
                    "quiz_score": None,
                    "quiz_passed": False,
                    "video_progress": 0,
                    "completed_at": None,
                    "created_at": None,
                    "updated_at": None,
                })

        completed_count = sum(1 for p in chapters_with_progress if p.get("status") == "completed")
        total = len(all_chapters)
        percentage = (completed_count / total * 100) if total > 0 else 0

        return {
            "total_chapters": total,
            "completed_chapters": completed_count,
            "progress_percentage": percentage,
            "chapters": chapters_with_progress,
        }

    # ============ 资源管理 ============

    def get_resources_by_chapter_id(self, chapter_id: int) -> List[OpenSpecCourseResource]:
        """根据章节 ID 获取资源"""
        return self.db.query(OpenSpecCourseResource).filter(
            OpenSpecCourseResource.chapter_id == chapter_id
        ).all()

    def get_resource_by_id(self, resource_id: int) -> Optional[OpenSpecCourseResource]:
        """根据 ID 获取资源"""
        return self.db.query(OpenSpecCourseResource).filter(OpenSpecCourseResource.id == resource_id).first()

    def create_resource(self, resource: ResourceCreate) -> OpenSpecCourseResource:
        """创建资源"""
        extra_data_str = None
        if resource.extra_data:
            import json
            extra_data_str = json.dumps(resource.extra_data, ensure_ascii=False)

        db_resource = OpenSpecCourseResource(
            chapter_id=resource.chapter_id,
            resource_type=resource.resource_type,
            title=resource.title,
            content=resource.content,
            extra_data=extra_data_str,
        )
        self.db.add(db_resource)
        self.db.commit()
        self.db.refresh(db_resource)
        return db_resource

    def update_resource(self, resource_id: int, resource: ResourceUpdate) -> Optional[OpenSpecCourseResource]:
        """更新资源"""
        db_resource = self.get_resource_by_id(resource_id)
        if not db_resource:
            return None

        update_data = resource.model_dump(exclude_unset=True)
        if "extra_data" in update_data and update_data["extra_data"] is not None:
            import json
            update_data["extra_data"] = json.dumps(update_data["extra_data"], ensure_ascii=False)

        for field, value in update_data.items():
            setattr(db_resource, field, value)

        self.db.commit()
        self.db.refresh(db_resource)
        return db_resource

    def delete_resource(self, resource_id: int) -> bool:
        """删除资源"""
        db_resource = self.get_resource_by_id(resource_id)
        if not db_resource:
            return False

        self.db.delete(db_resource)
        self.db.commit()
        return True
