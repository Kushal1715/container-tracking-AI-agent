import logging
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PNCT MCP Tool Server",
    description="MCP Tool layer for PNCT Container Query System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_SCRAPER_API_URL = "http://localhost:8002"

def get_scraper_api_url() -> str:
    return os.getenv("PNCT_SCRAPER_API_URL", DEFAULT_SCRAPER_API_URL)

class QueryContainerRequest(BaseModel):
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
        "service": "PNCT MCP Tool Server",
        "version": "1.0.0",
        "endpoints": {
            "query_container": "POST /tools/query_container",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "PNCT MCP Tool Server"}

@app.post("/tools/query_container")
async def tool_query_container(request: QueryContainerRequest):
    logger.info(f"Received query_container request: container_id={request.container_id}, intent={request.intent}")
    
    scraper_api_url = get_scraper_api_url()
    endpoint = f"{scraper_api_url}/scrape"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                endpoint,
                json={
                    "container_id": request.container_id,
                    "intent": request.intent
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully retrieved container information for {request.container_id}")
                return result
            elif response.status_code == 404:
                logger.warning(f"Container {request.container_id} not found")
                raise HTTPException(
                    status_code=404,
                    detail=f"Container {request.container_id} not found"
                )
            elif response.status_code == 500:
                logger.error(f"PNCT Scraper API error for container {request.container_id}")
                raise HTTPException(
                    status_code=500,
                    detail="PNCT Scraper API error"
                )
            else:
                logger.error(f"Unexpected status code {response.status_code} from scraper API")
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error from scraper API: {response.text}"
                )
                
    except httpx.TimeoutException:
        logger.error(f"Timeout calling PNCT Scraper API for container {request.container_id}")
        raise HTTPException(
            status_code=504,
            detail="Timeout waiting for PNCT Scraper API response"
        )
    except httpx.ConnectError:
        logger.error(f"Cannot connect to PNCT Scraper API at {scraper_api_url}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to PNCT Scraper API at {scraper_api_url}. Make sure the scraper API is running."
        )
    except httpx.NetworkError as e:
        logger.error(f"Network error calling PNCT Scraper API: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Network error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in query_container: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    uvicorn.run("mcp_tools.http_server:app", host="0.0.0.0", port=port, reload=True)
