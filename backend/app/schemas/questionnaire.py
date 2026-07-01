from pydantic import BaseModel


class QuestionOption(BaseModel):
    id: str
    text: str
    feasibility_score: float
    lead_score: float
    next_branch: str | None = None


class Question(BaseModel):
    id: str
    text: str
    dimension: str
    kind: str  # open_text / single_choice / multiple_choice / composite
    options: list[QuestionOption]
    max_feasibility_score: float
    max_lead_score: float
    is_scored: bool = True
    branch: str = "common"  # common / experienced / inexperienced / branch_decision
    display_id: str = ""
    display_order: int = 0
    sub_order: int = 1
    notes: str | None = None
    cap_note: str | None = None
    conflict_note: str | None = None


class QuestionnaireBranch(BaseModel):
    id: str
    name: str
    description: str
    questions: list[Question]
