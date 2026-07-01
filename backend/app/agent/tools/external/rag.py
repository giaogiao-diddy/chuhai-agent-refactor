from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.db.session import async_session
from app.schemas.rag import RagDocumentMatch
from app.services.rag_repository import search_rag_context


class RagSearchInput(BaseModel):
    query: str
    top_k: int = 3


class RagSearchOutput(BaseModel):
    matches: list[RagDocumentMatch]


async def rag_search_handler(
    inp: RagSearchInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        async with async_session() as db:
            matches = await search_rag_context(db, inp.query, inp.top_k)
        return ToolResult(data=RagSearchOutput(matches=matches))
    except Exception as e:
        return ToolResult(data=RagSearchOutput(matches=[]))
