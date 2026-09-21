import unittest
import asyncio
from app.slices.pod4_it_saga.saga_coordinator import execute_two_system_saga, AsyncSession
from app.slices.pod4_it_saga.service_immediately_client import create_it_provisioning_ticket, ServiceImmediatelyError

class TestPod4ItSaga(unittest.TestCase):
    def test_saga_happy_path(self):
        async def hr_step(): return "TX-HR-101"
        async def hr_compensate(tx_id): pass
        async def it_step(): return await create_it_provisioning_ticket("EMP1", "normal", {})
        
        session = AsyncSession()
        result = asyncio.run(execute_two_system_saga(session, "PROP-1", hr_step, hr_compensate, it_step))
        
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.hr_tx_id, "TX-HR-101")
        self.assertTrue(result.it_ticket_id.startswith("IT-TKT-"))

    def test_saga_partial_failure_rollback(self):
        compensate_called = False
        async def hr_step(): return "TX-HR-999"
        async def hr_compensate(tx_id):
            nonlocal compensate_called
            compensate_called = True
            
        async def it_step(): 
            return await create_it_provisioning_ticket("EMP1", "force_fail", {})
        
        session = AsyncSession()
        result = asyncio.run(execute_two_system_saga(session, "PROP-2", hr_step, hr_compensate, it_step))
        
        self.assertEqual(result.status, "ROLLBACK_EXECUTED")
        self.assertEqual(result.hr_tx_id, "TX-HR-999")
        self.assertIsNone(result.it_ticket_id)
        self.assertTrue(result.retry_task_id.startswith("TASK-RETRY-"))
        self.assertTrue(compensate_called)

if __name__ == "__main__":
    unittest.main()
