from typing import Literal

from pydantic import BaseModel, Field, field_validator

MemoryType = Literal["user", "feedback", "project", "reference"]


class MemoryFrontmatter(BaseModel):
    name: str
    description: str
    type: MemoryType


class MemoryEntry(BaseModel):
    path: str
    frontmatter: MemoryFrontmatter
    content: str


class MemoryRecallInput(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class MemoryRecallOutput(BaseModel):
    entries: list[MemoryEntry]


class MemorySaveInput(BaseModel):
    name: str
    description: str
    type: MemoryType
    content: str

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name 不能为空")
        if len(v) > 80:
            raise ValueError("name 长度不能超过 80 字符")
        if "\n" in v or "\r" in v:
            raise ValueError("name 不能包含换行符")
        return v

    @field_validator("description")
    @classmethod
    def _check_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description 不能为空")
        if len(v) > 200:
            raise ValueError("description 长度不能超过 200 字符")
        if "\n" in v or "\r" in v:
            raise ValueError("description 不能包含换行符")
        return v

    @field_validator("content")
    @classmethod
    def _check_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("content 不能为空")
        if len(v) > 4000:
            raise ValueError("content 长度不能超过 4000 字符")
        return v


class MemorySaveOutput(BaseModel):
    path: str
    index_updated: bool
