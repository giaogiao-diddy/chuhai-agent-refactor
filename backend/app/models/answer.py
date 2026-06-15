from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey

from app.core.database import Base


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("question_options.id"), nullable=False)
    score = Column(Integer, nullable=False)
