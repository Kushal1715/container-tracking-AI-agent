import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.worker import Worker
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_TEMPORAL_HOST = "localhost:7233"
DEFAULT_TEMPORAL_NAMESPACE = "default"
DEFAULT_TASK_QUEUE = "pnct-scraper-queue"

def get_temporal_host() -> str:
    return os.getenv("TEMPORAL_HOST", DEFAULT_TEMPORAL_HOST)

def get_temporal_namespace() -> str:
    return os.getenv("TEMPORAL_NAMESPACE", DEFAULT_TEMPORAL_NAMESPACE)

def get_task_queue() -> str:
    return os.getenv("TEMPORAL_TASK_QUEUE", DEFAULT_TASK_QUEUE)

async def main():
    temporal_host = get_temporal_host()
    temporal_namespace = get_temporal_namespace()
    task_queue = get_task_queue()
    
    logger.info(f"Connecting to Temporal server: {temporal_host}")
    logger.info(f"Namespace: {temporal_namespace}")
    logger.info(f"Task Queue: {task_queue}")
    
    try:
        client = await Client.connect(
            target_host=temporal_host,
            namespace=temporal_namespace
        )
        
        logger.info("Connected to Temporal server")
        
        from workflows.pnct_workflow import PNCTScrapeWorkflow
        from activities.pnct_activities import scrape_pnct_activity
        
        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[PNCTScrapeWorkflow],
            activities=[scrape_pnct_activity]
        )
        
        logger.info(f"Worker listening on task queue: {task_queue}")
        await worker.run()
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Error running worker: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
