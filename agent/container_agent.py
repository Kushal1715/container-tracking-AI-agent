import os
import logging
import httpx
import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MCP_SERVER_URL = "http://localhost:8001"

class ContainerAgent:
    def __init__(self, api_key: Optional[str] = None, mcp_server_url: str = DEFAULT_MCP_SERVER_URL):
        self.mcp_server_url = mcp_server_url.rstrip('/')
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
        self.client = genai.Client()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        self.tools = [
            {
                "name": "query_container",
                "description": "Query container information from PNCT.net. Use intent='all' to fetch all information when only container ID is provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID (e.g., ABCU1234567, TCLU9876543)"
                        },
                        "intent": {
                            "type": "string",
                            "description": "Intent: status, location, availability, holds, last_free_day, or 'all'",
                            "enum": ["status", "location", "availability", "holds", "last_free_day", "all"]
                        }
                    },
                    "required": ["container_id", "intent"]
                }
            }
        ]
    
    async def call_mcp_tool(self, container_id: str, intent: str) -> Dict[str, Any]:
        endpoint = f"{self.mcp_server_url}/tools/query_container"
        
        try:
            response = await self.http_client.post(
                endpoint,
                json={"container_id": container_id, "intent": intent}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling MCP tool: {e}")
            if e.response.status_code == 404:
                return {"error": "CONTAINER_NOT_FOUND", "message": f"Container {container_id} not found"}
            elif e.response.status_code == 500:
                return {"error": "SERVER_ERROR", "message": "PNCT Scraper API error"}
            else:
                return {"error": "API_ERROR", "message": f"Error calling MCP tool: {e.response.text}"}
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
            logger.error(f"Network error calling MCP tool: {e}")
            return {"error": "NETWORK_ERROR", "message": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error calling MCP tool: {e}")
            return {"error": "UNKNOWN_ERROR", "message": f"Unexpected error: {str(e)}"}
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        logger.info(f"Processing query: {user_query}")
        
        system_instruction = """You are an AI assistant that helps users query container information from PNCT.net.

Your tasks:
1. Extract the container ID from the user's query. Container IDs are typically 11 characters: 4 letters followed by 7 digits (e.g., ABCU1234567, TCLU9876543).
2. Determine the user's intent from the query. The intent can be one of:
   - "status": User wants to know the current status of the container
   - "location": User wants to know where the container is located
   - "availability": User wants to know if the container is available for pickup
   - "holds": User wants to know about any holds on the container
   - "last_free_day": User wants to know the last free day for the container
   - "all": User only provided a container ID without specifying what they want - fetch ALL available information

3. Once you have extracted the container ID and determined the intent, IMMEDIATELY call the query_container tool with both parameters.

4. After receiving the tool response, provide a DETAILED, comprehensive response to the user based on ALL the container information returned. Include ALL relevant details from the data.

CRITICAL INSTRUCTIONS FOR RESPONSES:
- For LOCATION queries: Include ALL location details such as current location, yard name, block, bay, position, container state, state, and coordinates if available.
- For STATUS queries: Include status, container state, location, and availability information.
- For AVAILABILITY queries: Include availability status, whether available for pickup, and any restrictions.
- For HOLDS queries: List ALL hold types, release statuses, and any hold details.
- For LAST_FREE_DAY queries: Include last free date, free days remaining, demurrage information, and any warnings.
- For "all" queries: Present ALL available information in organized sections: Status, Location, Availability, Holds, and Last Free Day. Include ALL details from each section.

- ALWAYS present the information in a clear, organized format
- Include ALL fields from the data that are relevant to the user's query
- Do NOT summarize or omit important details
- If a field is null or not available, you can mention it's not available, but still show all available information

Examples:
- "What is the status of container ABCU1234567?" → container_id="ABCU1234567", intent="status"
- "Where is TCLU9876543?" → container_id="TCLU9876543", intent="location"
- "Is ABCU1234567 available?" → container_id="ABCU1234567", intent="availability"
- "Any holds on TCLU9876543?" → container_id="TCLU9876543", intent="holds"
- "What's the last free day for ABCU1234567?" → container_id="ABCU1234567", intent="last_free_day"
- "ABCU1234567" → container_id="ABCU1234567", intent="all"

IMPORTANT:
- Always extract the container ID from the query - it's usually mentioned explicitly
- If the user provides ONLY a container ID without specifying what they want to know, use intent="all" to fetch all available information
- If the user doesn't specify an intent clearly, infer it from context (e.g., "where is" → location, "is available" → availability, "what is the status" → status)
- If you cannot extract a container ID, ask the user to provide it
- When intent is "all", the system will automatically fetch status, location, availability, holds, and last_free_day information
- PROVIDE COMPREHENSIVE, DETAILED RESPONSES - do not summarize or omit information
"""
        
        tools_config = types.Tool(function_declarations=self.tools)
        config = types.GenerateContentConfig(
            tools=[tools_config],
            system_instruction=system_instruction
        )
        
        user_content = types.Content(
            role="user",
            parts=[types.Part(text=user_query)]
        )
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[user_content],
                config=config
            )
            
            container_id = None
            intent = None
            ai_response = ""
            tool_result = None
            
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = part.function_call
                            if function_call.name == "query_container":
                                args = dict(function_call.args) if hasattr(function_call, 'args') else {}
                                container_id = args.get("container_id")
                                intent = args.get("intent")
                                
                                tool_result = await self.call_mcp_tool(container_id, intent)
                                
                                function_response_part = types.Part.from_function_response(
                                    name="query_container",
                                    response=tool_result
                                )
                                
                                final_response = self.client.models.generate_content(
                                    model="gemini-2.0-flash",
                                    contents=[
                                        user_content,
                                        candidate.content,
                                        types.Content(
                                            role="user",
                                            parts=[function_response_part]
                                        )
                                    ],
                                    config=config
                                )
                                
                                if final_response.text:
                                    ai_response = final_response.text
                                elif final_response.candidates and len(final_response.candidates) > 0:
                                    final_candidate = final_response.candidates[0]
                                    if final_candidate.content and final_candidate.content.parts:
                                        text_parts = []
                                        for p in final_candidate.content.parts:
                                            if hasattr(p, 'text') and p.text:
                                                if not (hasattr(p, 'function_call') and p.function_call):
                                                    text_parts.append(p.text)
                                        if text_parts:
                                            ai_response = ' '.join(text_parts)
                                
                                if not ai_response or ai_response.strip() == "":
                                    if "error" in tool_result:
                                        ai_response = f"Error: {tool_result.get('message', 'Unknown error')}"
                                    else:
                                        ai_response = f"Container {container_id} information: {json.dumps(tool_result, indent=2)}"
                                
                                break
                        
                        elif hasattr(part, 'text') and part.text:
                            if not (hasattr(part, 'function_call') and part.function_call):
                                ai_response += part.text + " "
            
            if not container_id or not intent:
                if not ai_response:
                    ai_response = "I need a container ID to query. Please provide a container ID in your query."
            
            ai_response = ai_response.strip()
            
            logger.info(f"Query processed. Container ID: {container_id}, Intent: {intent}")
            
            result = {
                "container_id": container_id,
                "intent": intent,
                "response": ai_response
            }
            
            if tool_result and "error" not in tool_result:
                result["raw_data"] = tool_result
            
            return result
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error processing query: {e}", exc_info=True)
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                return {
                    "container_id": None,
                    "intent": None,
                    "response": "I'm currently experiencing high demand from the AI service. Please wait a few moments and try again. The system is temporarily rate-limited.",
                    "error": "Rate limit exceeded. Please try again in a moment."
                }
            
            return {
                "container_id": None,
                "intent": None,
                "response": f"Error processing query: {error_str}",
                "error": error_str
            }
    
    async def close(self):
        await self.http_client.aclose()
