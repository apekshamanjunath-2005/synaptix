"""
Milestone 4 — Firestore Integration Verification Tests
Tests Firestore dual-mode client, Tasks CRUD, Notes CRUD,
REST API endpoints, and end-to-end multi-agent database persistence.
"""

import sys
import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.main import app
from app.database.firestore import firestore_service


class LiveFirestoreServer(threading.Thread):
    def __init__(self, port=8892):
        super().__init__(daemon=True)
        config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
        self.server = uvicorn.Server(config=config)
        self.port = port

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def make_request(url, method="GET", payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=50) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body


def test_milestone4_firestore():
    print("=================================================================")
    print(" 📦 RUNNING MILESTONE 4: FIRESTORE INTEGRATION VERIFICATION")
    print("=================================================================")

    # 1. Firestore Service Initialization Test
    print("\n[Test 1] Testing Firestore Service Client Initialization...")
    assert firestore_service.client is not None
    print(f"  ✅ Firestore service initialized successfully (Live Firebase: {firestore_service.is_live_firebase})")

    # 2. Tasks Collection CRUD Operations
    print("\n[Test 2] Testing Firestore Tasks Collection CRUD...")
    # 2a: Create task
    task = firestore_service.add_task(
        title="Deploy Synaptix to Cloud Run (M9)",
        due_date="2026-11-25",
        priority="high",
        status="pending"
    )
    assert task["id"].startswith("task-")
    assert task["title"] == "Deploy Synaptix to Cloud Run (M9)"
    assert task["priority"] == "high"
    task_id = task["id"]
    print(f"  ✅ add_task created document: {task_id}")

    # 2b: Read task
    fetched = firestore_service.get_task_by_id(task_id)
    assert fetched is not None
    assert fetched["title"] == task["title"]
    print(f"  ✅ get_task_by_id retrieved: {fetched['title']}")

    # 2c: Update task (and verify fresh updated snapshot is returned — bugfix verification!)
    updated = firestore_service.update_task(task_id, {"status": "completed", "priority": "low"})
    assert updated is not None
    assert updated["status"] == "completed", "Bugfix check: update_task must return fresh status, not stale!"
    assert updated["priority"] == "low"
    print(f"  ✅ update_task verified: status={updated['status']}, priority={updated['priority']}")

    # 2d: List tasks with filter
    completed_tasks = firestore_service.get_tasks(status="completed")
    assert any(t["id"] == task_id for t in completed_tasks)
    print(f"  ✅ get_tasks(status='completed') verified: found {len(completed_tasks)} tasks")

    # 2e: Delete task
    del_res = firestore_service.delete_task(task_id)
    assert del_res is True
    assert firestore_service.get_task_by_id(task_id) is None
    print(f"  ✅ delete_task successfully removed document: {task_id}")

    # 3. Notes Collection CRUD Operations
    print("\n[Test 3] Testing Firestore Notes Collection CRUD...")
    # 3a: Create note
    note = firestore_service.add_note(
        content="Firestore Spark plan offers 50,000 reads and 20,000 writes free daily.",
        title="Firestore Spark Plan Limits",
        tags=["database", "cloud", "pricing"]
    )
    assert note["id"].startswith("note-")
    note_id = note["id"]
    print(f"  ✅ add_note created document: {note_id}")

    # 3b: Search notes
    search_results = firestore_service.search_notes("50,000")
    assert len(search_results) >= 1
    assert search_results[0]["id"] == note_id
    print(f"  ✅ search_notes verified: found {len(search_results)} match(es) for '50,000'")

    # 3c: Delete note
    del_note_res = firestore_service.delete_note(note_id)
    assert del_note_res is True
    print(f"  ✅ delete_note successfully removed document: {note_id}")

    # 4. Live REST Endpoints Testing
    print("\n[Test 4] Testing Tasks and Notes REST Endpoints via Live HTTP Server...")
    server = LiveFirestoreServer(port=8892)
    server.start()
    time.sleep(1.2)
    base_url = "http://127.0.0.1:8892"

    try:
        # 4a: POST /api/tasks
        status_post_task, body_post_task = make_request(
            f"{base_url}/api/tasks",
            method="POST",
            payload={"title": "REST API Task", "priority": "medium", "status": "pending"}
        )
        assert status_post_task == 201
        created_api_task_id = body_post_task["task"]["id"]
        print(f"  ✅ POST /api/tasks returned 201 Created: {created_api_task_id}")

        # 4b: GET /api/tasks
        status_get_task, body_get_task = make_request(f"{base_url}/api/tasks")
        assert status_get_task == 200
        assert any(t["id"] == created_api_task_id for t in body_get_task["tasks"])
        print(f"  ✅ GET /api/tasks returned 200 OK: found {body_get_task['count']} tasks")

        # 4c: PATCH /api/tasks/{task_id}
        status_patch, body_patch = make_request(
            f"{base_url}/api/tasks/{created_api_task_id}",
            method="PATCH",
            payload={"status": "completed"}
        )
        assert status_patch == 200
        assert body_patch["task"]["status"] == "completed"
        print(f"  ✅ PATCH /api/tasks/{created_api_task_id} returned 200 OK")

        # 4d: DELETE /api/tasks/{task_id}
        status_del, _ = make_request(f"{base_url}/api/tasks/{created_api_task_id}", method="DELETE")
        assert status_del == 200
        print(f"  ✅ DELETE /api/tasks/{created_api_task_id} returned 200 OK")

        # 4e: POST /api/notes
        status_post_note, body_post_note = make_request(
            f"{base_url}/api/notes",
            method="POST",
            payload={"content": "Note created via REST endpoint", "title": "REST Note", "tags": ["test"]}
        )
        assert status_post_note == 201
        created_api_note_id = body_post_note["note"]["id"]
        print(f"  ✅ POST /api/notes returned 201 Created: {created_api_note_id}")

        # 4f: GET /api/notes?query=REST
        status_search_note, body_search_note = make_request(f"{base_url}/api/notes?query=REST")
        assert status_search_note == 200
        assert any(n["id"] == created_api_note_id for n in body_search_note["notes"])
        print(f"  ✅ GET /api/notes?query=REST returned 200 OK")

        # 4g: DELETE /api/notes/{note_id}
        status_del_note, _ = make_request(f"{base_url}/api/notes/{created_api_note_id}", method="DELETE")
        assert status_del_note == 200
        print(f"  ✅ DELETE /api/notes/{created_api_note_id} returned 200 OK")

        # 5. End-to-End: TaskAgent chat prompt creates real task in Firestore
        print("\n[Test 5] Testing End-to-End: TaskAgent creates actual task in Firestore...")
        status_chat, body_chat = make_request(
            f"{base_url}/api/chat",
            method="POST",
            payload={"message": "Add task: implement Google Calendar MCP integration"}
        )
        assert status_chat == 200
        # Query Firestore to prove the task was actually inserted by the agent!
        stored_tasks = firestore_service.get_tasks()
        agent_created = [t for t in stored_tasks if "Google Calendar MCP" in t["title"]]
        assert len(agent_created) >= 1, "Agent must insert real document into Firestore!"
        print(f"  ✅ End-to-End verified: TaskAgent inserted document '{agent_created[0]['title']}' into Firestore!")

    finally:
        server.stop()

    print("\n=================================================================")
    print(" 🎉 ALL MILESTONE 4 FIRESTORE TESTS PASSED SUCCESSFULLY!")
    print("=================================================================")


if __name__ == "__main__":
    test_milestone4_firestore()
