import logging
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any

logger = logging.getLogger(__name__)

@workflow.defn
class PNCTScrapeWorkflow:
    @workflow.run
    async def run(self, container_id: str, intent: str) -> Dict[str, Any]:
        workflow.logger.info(f"Workflow started: container_id={container_id}, intent={intent}")
        
        from activities.pnct_activities import scrape_pnct_activity
        
        result = await workflow.execute_activity(
            scrape_pnct_activity,
            args=[container_id, intent],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3
            )
        )
        
        workflow.logger.info(f"Workflow completed: container_id={container_id}, intent={intent}")
        return result
