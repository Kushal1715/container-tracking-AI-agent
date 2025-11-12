import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PNCT Container Query System",
    description="AI-powered container tracking system for PNCT.net",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContainerQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the status of container ABCU1234567?"
            }
        }

class ContainerQueryResponse(BaseModel):
    container_id: Optional[str] = None
    intent: Optional[str] = None
    response: str
    success: bool
    error: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {
        "service": "PNCT Container Query System",
        "version": "1.0.0",
        "endpoints": {
            "container_query": "POST /container/query",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "PNCT Container Query System"}

@app.post("/container/query", response_model=ContainerQueryResponse)
async def container_query(request: ContainerQueryRequest):
    logger.info(f"Received container query: {request.query}")
    
    try:
        from agent.container_agent import ContainerAgent
        
        agent = ContainerAgent()
        result = await agent.process_query(request.query)
        
        logger.info(f"Query processed. Container ID: {result.get('container_id')}, Intent: {result.get('intent')}")
        
        return ContainerQueryResponse(
            container_id=result.get("container_id"),
            intent=result.get("intent"),
            response=result.get("response", "Query processed successfully"),
            success=True,
            error=None,
            raw_data=result.get("raw_data")
        )
        
    except Exception as e:
        logger.error(f"Error processing container query: {e}", exc_info=True)
        return ContainerQueryResponse(
            container_id=None,
            intent=None,
            response=f"Error processing query: {str(e)}",
            success=False,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
