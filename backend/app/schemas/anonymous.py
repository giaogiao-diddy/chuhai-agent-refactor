import re

ANONYMOUS_USER_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
ANONYMOUS_USER_ID_ERROR = "anonymous_user_id 长度须为8-100位，仅允许字母、数字、-、_"


def validate_anonymous_user_id(value: str | None) -> str | None:
    if value is None:
        return value
    if len(value) < 8 or len(value) > 100:
        raise ValueError(ANONYMOUS_USER_ID_ERROR)
    if not re.fullmatch(ANONYMOUS_USER_ID_PATTERN, value):
        raise ValueError(ANONYMOUS_USER_ID_ERROR)
    return value
