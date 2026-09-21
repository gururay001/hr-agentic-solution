"""Two-System Saga State Machine Coordinator."""
import logging
from dataclasses import dataclass
from typing import Callable, Optional
import uuid

from .service_immediately_client import ServiceImmediatelyError

log = logging.getLogger("pod4.saga")

@dataclass
class SagaExecutionResult:
    status: str
    hr_tx_id: str
    it_ticket_id: Optional[str] = None
    retry_task_id: Optional[str] = None

# Mock async session type for type hint purposes
class AsyncSession:
    pass

async def execute_two_system_saga(
    session: AsyncSession,
    proposal_id: str,
    hr_step_fn: Callable,
    hr_compensate_fn: Callable,
    it_step_fn: Callable
) -> SagaExecutionResult:
    """Executes a cross-domain saga with deterministic compensating rollback."""
    log.info(f"SAGA_STARTED for proposal_id={proposal_id}")
    
    # Execute HR step
    hr_tx_id = await hr_step_fn()
    log.info(f"HR_COMMITTED tx_id={hr_tx_id}")

    try:
        # Execute IT step
        it_ticket_id = await it_step_fn()
        log.info(f"SAGA_COMPLETED hr_tx={hr_tx_id} it_tkt={it_ticket_id}")
        return SagaExecutionResult(
            status="COMPLETED",
            hr_tx_id=hr_tx_id,
            it_ticket_id=it_ticket_id
        )
    except (ServiceImmediatelyError, TimeoutError) as e:
        log.error(f"IT_FAILED: {e}")
        # Execute compensation
        await hr_compensate_fn(hr_tx_id)
        log.info(f"ROLLBACK_EXECUTED for hr_tx={hr_tx_id}")
        
        retry_task_id = f"TASK-RETRY-{uuid.uuid4().hex[:8]}"
        return SagaExecutionResult(
            status="ROLLBACK_EXECUTED",
            hr_tx_id=hr_tx_id,
            retry_task_id=retry_task_id
        )
