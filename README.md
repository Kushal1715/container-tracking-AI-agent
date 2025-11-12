# PNCT Container Query System

AI-powered container tracking system using Google Gemini and Temporal workflows.

## Quick Start

### Prerequisites
- Python 3.8+
- Temporal CLI
- Google Gemini API Key

### Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

### Start Services

1. **Temporal Server**:
```bash
temporal server start-dev
```

2. **Temporal Worker**:
```bash
python worker.py
```

3. **FastAPI Backend** (Terminal 1):
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **MCP Tool Server** (Terminal 2):
```bash
python -m mcp_tools.http_server
```

5. **Scraper API** (Terminal 3):
```bash
python scraper_api.py
```

6. **Streamlit Chat Interface** (Terminal 4):
```bash
streamlit run streamlit_app.py
```

## Usage

### API Endpoint

**POST** `/container/query`

```bash
curl -X POST http://localhost:8000/container/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of container ABCU1234567?"}'
```

### Chat Interface

Open http://localhost:8501 in your browser.

## Project Structure

```
.
├── main.py                 # FastAPI backend
├── scraper_api.py          # Scraper API
├── worker.py               # Temporal worker
├── streamlit_app.py        # Chat interface
├── agent/                  # AI Agent
├── mcp_tools/              # MCP Tool layer
├── workflows/              # Temporal workflows
└── activities/             # Temporal activities
```

## Configuration

Environment variables (optional):
- `GEMINI_API_KEY` - Required
- `MCP_SERVER_PORT` - Default: 8001
- `SCRAPER_API_PORT` - Default: 8002
- `TEMPORAL_HOST` - Default: localhost:7233
- `TEMPORAL_NAMESPACE` - Default: default
