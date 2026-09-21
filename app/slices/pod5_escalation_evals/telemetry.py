"""Pod 5 OpenTelemetry FinOps & CSAT Telemetry Collector."""
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("pod5.telemetry")

@dataclass
class TokenAttribution:
    model: str
    input_tokens: int
    output_tokens: int
    department_cost_center: str

@dataclass
class CSATRecord:
    session_id: str
    rating: int  # 1 to 5
    feedback: Optional[str] = None

def record_token_usage(attribution: TokenAttribution) -> None:
    """Record FinOps token consumption and cost center attribution."""
    log.info(f"FINOPS_ATTRIBUTION model={attribution.model} in={attribution.input_tokens} out={attribution.output_tokens} cost_center={attribution.department_cost_center}")

def record_csat(record: CSATRecord) -> float:
    """Record 1-5 star CSAT feedback rating (target >= 4.2/5.0)."""
    if not (1 <= record.rating <= 5):
        raise ValueError("CSAT rating must be between 1 and 5.")
    log.info(f"CSAT_RECORD session_id={record.session_id} rating={record.rating} feedback={record.feedback!r}")
    return float(record.rating)
