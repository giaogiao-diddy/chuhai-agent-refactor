"""市场准入分析 Skill — 组合 RAG + 关税查询"""
from app.agent.skills.registry import BundledSkill
from app.schemas.agent_state import AgentState


class MarketAccessSkill(BundledSkill):
    def __init__(self):
        super().__init__(
            name="market-access",
            description="分析目标市场准入门槛：关税、认证要求、合规清单",
            when_to_use="用户确定目标市场后，需要了解该市场的准入条件时触发",
            user_invocable=True,
        )

    async def execute(self, state: AgentState, tool_executor, **kwargs) -> str:
        product = None
        market = None
        if state.slots.main_product and state.slots.main_product.value:
            product = str(state.slots.main_product.value)
        if state.slots.target_market and state.slots.target_market.value:
            market = str(state.slots.target_market.value)

        if not product or not market:
            return "需要先确认主营产品和目标市场才能进行市场准入分析。"

        # 1. RAG 检索认证知识
        from app.agent.tools.external.rag import RagSearchInput
        rag_result = await tool_executor.execute("rag.search", RagSearchInput(
            query=f"{product} {market} 出口认证 关税 合规",
            top_k=3,
        ))

        lines = [f"## {product} → {market} 市场准入分析\n"]
        lines.append(f"**目标市场**: {market}")
        lines.append(f"**主营产品**: {product}\n")

        # 2. RAG 结果
        if rag_result.error is None and rag_result.data is not None:
            matches = rag_result.data.matches or []
            if matches:
                lines.append("### 参考知识")
                for m in matches[:3]:
                    lines.append(f"- **{m.title}** ({m.source or '未知来源'}): {m.content[:300]}")

        lines.append("\n### 建议下一步")
        lines.append("1. 确认目标市场强制认证要求（CE/FDA/当地标准）")
        lines.append("2. 核算关税成本（可连接关税 MCP Server 获取实时数据）")
        lines.append("3. 确认物流时效和清关流程")

        return "\n".join(lines)
