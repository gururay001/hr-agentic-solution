"""Isolated Sub-Agent for pod2_policy_rag — auto-discovered by app/agent.py."""

from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from app.core.config import settings
from app.slices.pod2_policy_rag.retriever import retrieve_authorized_policy_chunks


async def search_hr_policy(
    query: str,
    country_code: str = "SG",
    role: str = "IC",
) -> dict[str, Any]:
    """ADK Tool: Executes synchronous `<2ms` Pre-Retrieval Entitlement Gate & Hybrid Policy RAG.

    Always returns `[DOC_ID#section]` citations or abstains when rerank confidence < 0.75 or
    when restricted by `country_code` / `min_role`.
    """
    result = await retrieve_authorized_policy_chunks(
        query=query,
        user_country=country_code,
        user_role=role,
    )
    citations = [
        {
            "doc_id": c.doc_id,
            "section_anchor": c.section_anchor,
            "citation": c.citation,
            "snippet": c.content_text,
            "rerank_score": c.rerank_score,
        }
        for c in result.chunks
    ]
    formatted_context = (
        "\n".join(f"{c.citation}: {c.content_text}" for c in result.chunks)
        if not result.abstained
        else result.abstention_reason
    )
    return {
        "abstained": result.abstained,
        "abstention_reason": result.abstention_reason,
        "pre_filter_latency_ms": result.pre_filter_latency_ms,
        "highest_score": result.highest_score,
        "citations": citations,
        "formatted_context": formatted_context,
    }


specialist_agent = LlmAgent(
    name="policy_rag_agent",
    model=settings.GEMINI_FLASH_MODEL,
    description="Pod 2: <2ms Pre-Retrieval Entitlement Gate & Hybrid Policy RAG with [DOC_ID#section] citations.",
    instruction=(
        "You are `policy_rag_agent` (Pod 2: `<2ms` Pre-Retrieval Entitlement Gate & Hybrid Policy RAG). "
        "Always call `search_hr_policy` with the caller's `country_code` and `role`. "
        "Every factual policy claim MUST include its inline `[DOC_ID#section]` citation badge. "
        "If `abstained` is True (either because the document requires higher role entitlements like `EXEC` "
        "or because the Vertex AI Reranker confidence score is `< 0.75`), you MUST refuse/abstain and "
        "explain the entitlement restriction or request clarification."
    ),
    tools=[search_hr_policy],
)


def get_agent_tool() -> AgentTool:
    """Returns the AgentTool wrapper for automatic registration in HRSupervisorAgent."""
    return AgentTool(agent=specialist_agent)
