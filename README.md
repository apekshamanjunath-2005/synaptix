# Synaptix — Multi-Agent AI Personal Productivity Assistant

Synaptix is a production-grade, multi-agent AI personal productivity assistant built with **Google Gemini 2.5 Flash**, **Google ADK (Agent Development Kit)**, **FastAPI**, **Firebase Firestore**, **Model Context Protocol (MCP)**, and **OpenWeatherMap**.

It operates under a strict **Zero-Cost Policy (₹0 Budget)** with application-level rate limiters and disk-persisted quota guards.

---

## 🏛 System Architecture & Multi-Agent Roster

Synaptix delegates user requests across a root coordinator and four specialist agents:

```
                          ┌────────────────────────┐
                          │   User Natural Prompt  │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │    CoordinatorAgent    │
                          │   (Root Orchestrator)  │
                          └───────────┬────────────┘
         ┌──────────────────┬─────────┴─────────┬──────────────────┐
         │                  │                   │                  │
         ▼                  ▼                   ▼                  ▼
┌─────────────────┐ ┌───────────────┐ ┌───────────────────┐ ┌──────────────────────┐
│    TaskAgent    │ │  NotesAgent   │ │   CalendarAgent   │ │ SmartDayPlannerAgent │
├─────────────────┤ ├───────────────┤ ├───────────────────┤ ├──────────────────────┤
│ • Create Tasks  │ │ • Save Notes  │ │ • Schedule Events │ │ • Synthesize Schedule│
│ • List & Query  │ │ • Fast Search │ │ • Check Conflicts │ │ • Priority Slotting  │
│ • Update Status │ │ • Tag Indexing│ │ • List Day Events │ │ • Weather Advisory   │
│ • Firestore DB  │ │ • Firestore DB│ │ • Calendar MCP    │ │ • Multi-Agent Co-ord │
└─────────────────┘ └───────────────┘ └───────────────────┘ └──────────────────────┘
```

1. **Coordinator Agent:** Root intent analyzer and dispatcher. Dispatches single or multi-domain tasks and synthesizes final responses.
2. **Task Agent:** Manages task lifecycle (creation, due dates, priority, status) in Firebase Firestore.
3. **Notes Agent:** Captures, categorizes, and searches meeting notes and ideas with keyword indexing in Firestore.
4. **Calendar Agent:** Integrates with Google Calendar via MCP to book meetings, list agendas, and detect timeslot conflicts.
5. **Smart Day Planner Agent:** Synthesizes pending tasks, calendar events, and real-time weather to construct realistic daily timetables.

---

## 🛠 Technology Stack

- **Language:** Python 3.12
- **Agent Framework:** Google ADK (`google-adk>=2.14.0`)
- **LLM:** Google Gemini 2.5 Flash (`google-genai>=2.30.0`)
- **API Framework:** FastAPI, Uvicorn, Pydantic v2
- **Database:** Firebase Firestore (`firebase-admin`, `google-cloud-firestore`)
- **Protocol:** Model Context Protocol (`mcp>=2.3.0`)
- **HTTP Client:** HTTPX (`httpx>=0.28.1`)
- **Containerization:** Docker (`python:3.12-slim`)
- **Cloud Deployment:** Google Cloud Run (Free Tier)

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.12+
- Git

### 2. Virtual Environment Setup
```powershell
# Clone and navigate
cd c:\synaptix

# Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
*(Synaptix works 100% out-of-the-box in Safe Zero-Cost Fallback Mode even without external API keys).*

### 4. Run the Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access the Web Dashboard
- **Web UI Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **System Health & Telemetry:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 🧪 Master Automated Test Suite

Run all milestone verification tests in one command:
```powershell
.\.venv\Scripts\python.exe tests/run_all_tests.py
```

### Individual Test Suites:
- Milestone 1 (Foundation): `.\.venv\Scripts\python.exe tests/verify_milestone1_comprehensive.py`
- Milestone 2 (Gemini Integration): `.\.venv\Scripts\python.exe tests/test_milestone2.py`
- Milestone 3 (Multi-Agent System): `.\.venv\Scripts\python.exe tests/test_milestone3.py`
- Milestone 4 (Firestore CRUD): `.\.venv\Scripts\python.exe tests/test_milestone4.py`
- Milestone 5 (Calendar MCP): `.\.venv\Scripts\python.exe tests/test_milestone5.py`
- Milestone 6 (Weather Integration): `.\.venv\Scripts\python.exe tests/test_milestone6.py`
- Milestone 7 (Smart Day Planner): `.\.venv\Scripts\python.exe tests/test_milestone7.py`
- Milestone 8 (UI & Dashboard): `.\.venv\Scripts\python.exe tests/test_milestone8.py`

---

## 🐳 Docker & Cloud Run Deployment

### Local Container Build:
```bash
docker build -t synaptix:latest .
docker run -p 8000:8000 synaptix:latest
```

### Zero-Cost Google Cloud Run Deployment:
See the detailed guide in [docs/deployment_cloud_run.md](docs/deployment_cloud_run.md).
```bash
gcloud run deploy synaptix \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 40 \
  --cpu 1 \
  --memory 512Mi \
  --cpu-throttling
```
