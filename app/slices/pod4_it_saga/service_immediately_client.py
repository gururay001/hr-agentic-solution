"""ServiceImmediately IT MCP Client."""
import asyncio
from uuid import uuid4

class ServiceImmediatelyError(Exception):
    pass

# We simulate the AsyncLimiter logic for 25 RPS
class AsyncLimiter:
    def __init__(self, max_rate: int, time_period: float):
        self.max_rate = max_rate
        self.time_period = time_period
        self._tokens = max_rate
        self._last_check = asyncio.get_event_loop().time()

    async def acquire(self):
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_check
        self._tokens += elapsed * (self.max_rate / self.time_period)
        if self._tokens > self.max_rate:
            self._tokens = self.max_rate
        self._last_check = now

        if self._tokens < 1:
            wait_time = (1 - self._tokens) * (self.time_period / self.max_rate)
            await asyncio.sleep(wait_time)
            self._tokens = 0
            self._last_check = asyncio.get_event_loop().time()
        else:
            self._tokens -= 1

si_limiter = AsyncLimiter(max_rate=25, time_period=1.0)

async def create_it_provisioning_ticket(employee_id: str, category: str, details: dict) -> str:
    await si_limiter.acquire()
    # Simulate API failure for certain conditions
    if category == "force_fail":
        raise ServiceImmediatelyError("Simulated IT provisioning failure")
    return f"IT-TKT-{uuid4().hex[:8]}"

async def get_ticket_status(ticket_id: str) -> dict:
    await si_limiter.acquire()
    return {"ticket_id": ticket_id, "status": "PENDING"}
