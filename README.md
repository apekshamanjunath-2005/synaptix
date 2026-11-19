# Synaptix — Multi-Agent AI Personal Productivity Assistant

Synaptix is an intelligent personal productivity assistant powered by Google Gemini and Google ADK (Agent Development Kit). It delegates user requests across five specialized AI agents to manage tasks, notes, calendar events, and daily planning through natural language.

---

## 🏛 Architecture

Synaptix uses a coordinated multi-agent architecture:

1. **Coordinator Agent:** Understands user intent, delegates work to specialized agents, synthesizes responses.
2. **Task Agent:** Handles task creation, querying, priority updates, and status tracking (Firestore).
3. **Notes Agent:** Manages personal and project notes with keyword and semantic search (Firestore).
4. **Calendar Agent:** Google Calendar MCP integration for events, scheduling, and conflict detection.
5. **Smart Day Planner Agent:** Aggregates pending tasks, calendar events, and weather forecasts to generate conflict-free daily schedules.

---

## 💰 Strict Zero-Cost Policy (₹0 Budget)

Synaptix is engineered from the ground up to operate entirely on **free-tier services**:
- **Gemini 2.5 Flash:** Google AI Studio free tier.
- **Firebase Firestore:** Spark Plan (₹0 / 50k reads, 20k writes/day).
- **Google Calendar:** Official Google OAuth & MCP (free).
- **OpenWeatherMap:** Free OneCall / Current Weather API (1,000 calls/day free).
- **Application Safeguards:** Configurable daily request caps, token limits, and bounded tool calls to prevent accidental billing.

---

## 🚀 Quickstart (Milestone 1)

### 1. Prerequisites
- Python 3.12+
- Git

### 2. Environment Setup
```powershell
# Clone or navigate to the repository
cd c:\synaptix

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

### 4. Run the Server
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access the Application
- **Frontend Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Endpoint:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
