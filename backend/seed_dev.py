"""开发环境种子数据脚本 — SQLite 模式下使用"""
import json
import os
os.environ["LB_DATABASE_URL"] = "sqlite:///./dev.db"

from app.core.database import SessionLocal, init_db
from app.models.question import Question, QuestionOption

init_db()

db = SessionLocal()
with open("tests/fixtures/sample_questions.json", encoding="utf-8") as f:
    fixture = json.load(f)

for q_data in fixture["questions"]:
    q = Question(
        id=q_data["id"], title=q_data["title"],
        description=q_data.get("description", ""),
        dimension=q_data["dimension"], sort_order=q_data["sort_order"], is_active=True,
    )
    db.add(q)
    for opt in q_data["options"]:
        db.add(QuestionOption(
            id=opt["id"], question_id=q.id, option_text=opt["text"],
            score=opt["score"], sort_order=opt["sort_order"],
        ))
db.commit()
db.close()
print(f"✅ Seeded {len(fixture['questions'])} questions")
