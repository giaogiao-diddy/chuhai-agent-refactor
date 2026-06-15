from __future__ import annotations
"""题库接口"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import Question
from app.schemas.question import QuestionListResponse, QuestionResponse, OptionResponse

router = APIRouter(tags=["questions"])


@router.get("/questions", response_model=QuestionListResponse)
def get_questions(db: Session = Depends(get_db)):
    """获取全部活跃题目及选项，按 sort_order 排序"""
    questions = (
        db.query(Question)
        .filter_by(is_active=True)
        .order_by(Question.sort_order)
        .all()
    )
    result = []
    for q in questions:
        opts = sorted(q.options, key=lambda o: o.sort_order)
        result.append(
            QuestionResponse(
                id=q.id,
                title=q.title,
                description=q.description or "",
                dimension=q.dimension,
                sort_order=q.sort_order,
                options=[
                    OptionResponse(
                        id=o.id,
                        text=o.option_text,
                        score=o.score,
                        sort_order=o.sort_order,
                    )
                    for o in opts
                ],
            )
        )
    return QuestionListResponse(questions=result, total=len(result))
