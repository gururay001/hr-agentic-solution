"""Pod 5 Sentiment Escalation & Warm Handoff Service."""
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

@dataclass
class ConversationTurn:
    role: str
    content: str
    redacted_content: str
    sentiment_score: float

@dataclass
class WarmHandoffCase:
    case_id: str
    priority: str
    assigned_queue: str
    redacted_summary: List[str]
    status: str

def should_trigger_warm_handoff(sentiment_score: float, rag_confidence: float, consecutive_fallbacks: int) -> bool:
    """Determine if warm handoff to live HR specialist should be triggered."""
    if sentiment_score < -0.40:
        return True
    if rag_confidence < 0.75:
        return True
    if consecutive_fallbacks >= 2:
        return True
    return False

async def create_warm_handoff_case(session_id: UUID, turns: List[ConversationTurn], category: str = "general") -> WarmHandoffCase:
    """Create Priority P2 ServiceImmediately HR Case with redacted 5-turn summary."""
    redacted_summary = [t.redacted_content for t in turns[-5:]]
    case_id = f"SI-HR-{abs(hash(str(session_id))) % 100000:05d}"
    
    return WarmHandoffCase(
        case_id=case_id,
        priority="P2",
        assigned_queue=f"People_Partner_{category}_Queue",
        redacted_summary=redacted_summary,
        status="WARM_HANDOFF_CREATED"
    )
