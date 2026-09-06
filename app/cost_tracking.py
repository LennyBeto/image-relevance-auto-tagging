"""Per-call cost tracking. Every vision/embedding call gets one row here,
attributed to the job that triggered it, per PROBE 6 in the brief."""
from sqlalchemy.orm import Session

from app.models import CostLog

# Rough, documented public per-unit prices for the free-tier-adjacent models.
# These are estimates for visibility, not a billing system.
PRICE_PER_1K_UNITS = {
    ("gemini", "vision"): 0.0,      # free tier while under quota
    ("gemini", "embedding"): 0.0,   # free tier while under quota
    ("ollama", "vision"): 0.0,      # local, no API cost
    ("ollama", "embedding"): 0.0,   # local, no API cost
}


def log_cost(
    db: Session,
    *,
    job_id: str | None,
    call_type: str,
    provider: str,
    model: str,
    input_units: int,
    output_units: int = 0,
) -> CostLog:
    rate = PRICE_PER_1K_UNITS.get((provider, call_type), 0.0)
    estimated = ((input_units + output_units) / 1000) * rate

    entry = CostLog(
        job_id=job_id,
        call_type=call_type,
        provider=provider,
        model=model,
        input_units=input_units,
        output_units=output_units,
        estimated_cost_usd=estimated,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
