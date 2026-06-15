from __future__ import annotations
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    description = Column(String(512), default="")
    dimension = Column(String(64), nullable=False)  # company / business
    sort_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    options = relationship("QuestionOption", order_by="QuestionOption.sort_order")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text = Column(String(256), nullable=False)
    score = Column(Integer, nullable=False)  # 1-4
    sort_order = Column(Integer, nullable=False)
