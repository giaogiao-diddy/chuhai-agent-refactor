from app.agent.skills.bundled.market_access import MarketAccessSkill
from app.agent.skills.registry import register_bundled_skill


def register_all_bundled_skills() -> None:
    register_bundled_skill(MarketAccessSkill())
