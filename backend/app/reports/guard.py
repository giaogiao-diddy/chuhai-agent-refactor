from app.schemas.report import UserReport

FORBIDDEN_USER_REPORT_FIELDS = {
    "lead_score",
    "lead_priority",
    "sales_followup",
    "consultant_notes",
    "recommended_next_action",
}

FORBIDDEN_STRINGS = [
    "lead_score",
    "lead_priority",
    "sales_followup",
    "consultant_notes",
    "顾问跟进",
    "销售话术",
]


def assert_user_report_safe(report: UserReport) -> None:
    data = report.model_dump()
    for key in FORBIDDEN_USER_REPORT_FIELDS:
        if key in data:
            raise ValueError(f"UserReport 包含禁止字段: {key}")

    text = str(data)
    for word in FORBIDDEN_STRINGS:
        if word in text:
            raise ValueError(f"UserReport 包含禁止词: {word}")
