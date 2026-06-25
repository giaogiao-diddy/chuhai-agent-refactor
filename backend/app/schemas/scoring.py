from pydantic import BaseModel


class DimensionScore(BaseModel):
    name: str
    raw_score: int
    max_score: int
    normalized_score: int


class ScoringInput(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    product: str | None = None
    target_market: str | None = None
    feasibility_dimensions: dict[str, int]
    lead_dimensions: dict[str, int]


class ScoringResult(BaseModel):
    feasibility_score: int
    lead_score: int
    display_score: int
    tag: str
    tag_explanation: str
    preliminary_judgment: str
    dimension_scores: list[DimensionScore]
    strengths: list[str]
    risks: list[str]
    lead_priority: str
