import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PNCT Scraper API",
    description="API that triggers Temporal workflows for scraping PNCT.net container data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_TEMPORAL_HOST = "localhost:7233"
DEFAULT_TEMPORAL_NAMESPACE = "default"

def get_temporal_host() -> str:
    return os.getenv("TEMPORAL_HOST", DEFAULT_TEMPORAL_HOST)

def get_temporal_namespace() -> str:
    return os.getenv("TEMPORAL_NAMESPACE", DEFAULT_TEMPORAL_NAMESPACE)

class ScrapeRequest(BaseModel):
    container_id: str = Field(..., min_length=1)
    intent: str = Field(...)
    
    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v):
        valid_intents = ["status", "location", "availability", "holds", "last_free_day", "all"]
        if v not in valid_intents:
            raise ValueError(f"intent must be one of: {', '.join(valid_intents)}")
        return v

@app.get("/")
async def root():
    return {
        "service": "PNCT Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "POST /scrape",
            "health": "GET /health",
            "docs": "GET /docs"
        },
        "temporal": {
            "host": get_temporal_host(),
            "namespace": get_temporal_namespace()
        }
    }

@app.get("/health")
async def health():
    try:
        from temporalio.client import Client
        temporal_available = True
    except ImportError:
        temporal_available = False
    
    return {
        "status": "healthy",
        "service": "PNCT Scraper API",
        "temporal_available": temporal_available,
        "temporal_host": get_temporal_host()
    }

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    logger.info(f"Received scrape request: container_id={request.container_id}, intent={request.intent}")
    
    try:
        from temporalio.client import Client
        from workflows.pnct_workflow import PNCTScrapeWorkflow
    except ImportError as e:
        logger.error(f"Temporal client or workflow not available: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Temporal client not available: {str(e)}"
        )
    
    try:
        temporal_host = get_temporal_host()
        temporal_namespace = get_temporal_namespace()
        
        client = await Client.connect(
            target_host=temporal_host,
            namespace=temporal_namespace
        )
        
        handle = await client.start_workflow(
            PNCTScrapeWorkflow.run,
            args=[request.container_id, request.intent],
            id=f"pnct-scrape-{request.container_id}-{request.intent}",
            task_queue="pnct-scraper-queue"
        )
        
        result = await handle.result()
        
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
        else:
            data = result
        
        return {
            "container_id": request.container_id,
            "intent": request.intent,
            "data": data,
            "workflow_id": handle.id
        }
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}", exc_info=True)
        
        if "Connection" in str(e) or "connect" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Temporal server at {temporal_host}"
            )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error executing workflow: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SCRAPER_API_PORT", "8002"))
    uvicorn.run("scraper_api:app", host="0.0.0.0", port=port, reload=True)
