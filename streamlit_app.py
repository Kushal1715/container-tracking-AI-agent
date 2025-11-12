import streamlit as st
import httpx
from datetime import datetime
from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="PNCT Container Query System",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
API_ENDPOINT = f"{API_BASE_URL}/container/query"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .stTextInput > div > div > input {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_status" not in st.session_state:
    st.session_state.api_status = "unknown"
if "api_error" not in st.session_state:
    st.session_state.api_error = None

def check_api_health() -> bool:
    try:
        response = httpx.get(HEALTH_ENDPOINT, timeout=10.0)
        if response.status_code == 200:
            st.session_state.api_status = "healthy"
            st.session_state.api_error = None
            return True
        else:
            st.session_state.api_status = "unhealthy"
            st.session_state.api_error = f"HTTP {response.status_code}: {response.text}"
            return False
    except httpx.ConnectError:
        st.session_state.api_status = "error"
        st.session_state.api_error = f"Connection Error: Cannot connect to {API_BASE_URL}. Make sure the FastAPI server is running on port 8000."
        return False
    except httpx.TimeoutException:
        st.session_state.api_status = "error"
        st.session_state.api_error = f"Timeout: The API did not respond within 10 seconds. Check if the server is running."
        return False
    except Exception as e:
        st.session_state.api_status = "error"
        st.session_state.api_error = f"Error: {str(e)}"
        return False

def query_container(query: str) -> Dict[str, Any]:
    try:
        if st.session_state.api_status != "healthy":
            check_api_health()
            if st.session_state.api_status != "healthy":
                return {
                    "success": False,
                    "error": "API Not Available",
                    "response": f"API connection error: {st.session_state.api_error or 'Unknown error'}. Please check if the FastAPI server is running on {API_BASE_URL}"
                }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                API_ENDPOINT,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        st.session_state.api_status = "error"
        st.session_state.api_error = f"Cannot connect to {API_BASE_URL}"
        return {
            "success": False,
            "error": "Connection Error",
            "response": f"Could not connect to API at {API_BASE_URL}. Make sure the FastAPI server is running."
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Timeout",
            "response": f"Request timed out. The API took too long to respond."
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}",
            "response": f"Error: {e.response.text}"
        }
    except httpx.RequestError as e:
        st.session_state.api_status = "error"
        st.session_state.api_error = str(e)
        return {
            "success": False,
            "error": "Request Error",
            "response": f"Could not connect to API: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": f"Unexpected error: {str(e)}"
        }

def format_response(response_data: Dict[str, Any]) -> str:
    if not response_data.get("success", False):
        return response_data.get("response", "Error processing query")
    return response_data.get("response", "")

st.markdown("""
<div class="main-header">
    <h1>🚢 PNCT Container Query System</h1>
    <p>AI-Powered Container Tracking</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📊 System Status")
    
    if st.button("🔄 Check API Status"):
        check_api_health()
    
    status = st.session_state.api_status
    if status == "healthy":
        st.success("✅ API Connected")
    elif status == "unhealthy":
        st.warning("⚠️ API Unhealthy")
        if st.session_state.api_error:
            st.caption(f"Error: {st.session_state.api_error}")
    elif status == "error":
        st.error("❌ API Connection Error")
        if st.session_state.api_error:
            with st.expander("🔍 Error Details", expanded=True):
                st.error(st.session_state.api_error)
                st.info(f"**API URL:** {API_BASE_URL}")
                st.info("**Troubleshooting:**")
                st.markdown("""
                1. Make sure the FastAPI server is running:
                   ```bash
                   python main.py
                   # or
                   uvicorn main:app --reload
                   ```
                2. Check if the server is listening on port 8000
                3. Verify the API_BASE_URL in your .env file (if set)
                """)
    else:
        st.info("ℹ️ Status Unknown")
        if st.button("🔄 Check Now"):
            check_api_health()
            st.rerun()
    
    st.markdown("---")
    
    st.header("📝 Example Queries")
    example_queries = [
        "What is the status of container ABCU1234567?",
        "Where is container TCLU9876543?",
        "Is container ABCU1234567 available?",
        "Any holds on container TCLU9876543?",
        "What is the last free day for container ABCU1234567?"
    ]
    
    for example in example_queries:
        if st.button(f"💬 {example}", key=f"example_{example[:20]}"):
            st.session_state.example_query = example
    
    st.markdown("---")
    
    st.header("ℹ️ About")
    st.markdown("""
    This system uses:
    - **Google Gemini AI** for natural language processing
    - **Temporal Workflows** for reliable scraping
    - **FastAPI** backend for API services
    
    **Supported Intents:**
    - Status
    - Location
    - Availability
    - Holds
    - Last Free Day
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

if st.session_state.api_status == "unknown":
    check_api_health()

if "example_query" in st.session_state:
    query = st.session_state.example_query
    del st.session_state.example_query
    
    st.session_state.messages.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now()
    })
    
    with st.spinner("Processing your query..."):
        response_data = query_container(query)
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": format_response(response_data),
        "response_data": response_data,
        "timestamp": datetime.now()
    })
    
    st.rerun()

st.header("💬 Chat")

if len(st.session_state.messages) == 0:
    st.info("""
    👋 **Welcome to the PNCT Container Query System!**
    
    I can help you track containers by answering questions like:
    - What is the status of container ABCU1234567?
    - Where is container TCLU9876543?
    - Is container ABCU1234567 available?
    - Any holds on container TCLU9876543?
    - What is the last free day for container ABCU1234567?
    
    Type your question below or click an example query from the sidebar!
    """)

for i, message in enumerate(st.session_state.messages):
    role = message["role"]
    content = message["content"]
    timestamp = message.get("timestamp", datetime.now())
    
    with st.chat_message(role):
        st.markdown(content)
        
        if role == "assistant" and "response_data" in message:
            response_data = message["response_data"]
            
            if response_data.get("raw_data"):
                raw_data = response_data["raw_data"]
                
                if st.checkbox("🔍 Show Raw JSON", key=f"raw_json_{i}"):
                    st.json(raw_data)
        
        st.caption(f"🕐 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

user_query = st.chat_input("Ask about a container... (e.g., What is the status of container ABCU1234567?)")

if user_query:
    st.session_state.messages.append({
        "role": "user",
        "content": user_query,
        "timestamp": datetime.now()
    })
    
    with st.spinner("🤔 Processing your query..."):
        response_data = query_container(user_query)
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": format_response(response_data),
        "response_data": response_data,
        "timestamp": datetime.now()
    })
    
    st.rerun()

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>PNCT Container Query System v1.0.0 | Powered by Gemini AI & Temporal</p>
</div>
""", unsafe_allow_html=True)
