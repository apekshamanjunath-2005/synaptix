"""
Database & Workspace Purge Script
Safely wipes all trial/test data across live Firestore and local JSON stores
WITHOUT deleting user OAuth credentials or touching real Google Calendar events.
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.firestore import firestore_service
from app.tools.calendar_mcp import calendar_mcp

def purge_all():
    print("==================================================")
    print(" 🧹 SYNAPTIX COMPLETE WORKSPACE PURGE")
    print("==================================================")

    client = firestore_service.client
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Purge tasks
    print("\n[1/7] Purging 'tasks' collection in Firestore...")
    tasks = list(client.collection("tasks").stream())
    for t in tasks:
        t.reference.delete()
    print(f"  ✅ Deleted {len(tasks)} tasks.")

    # 2. Purge notes
    print("\n[2/7] Purging 'notes' collection in Firestore...")
    notes = list(client.collection("notes").stream())
    for n in notes:
        n.reference.delete()
    print(f"  ✅ Deleted {len(notes)} notes.")

    # 3. Purge reminders
    print("\n[3/7] Purging 'reminders' collection in Firestore...")
    reminders = list(client.collection("reminders").stream())
    for r in reminders:
        r.reference.delete()
    print(f"  ✅ Deleted {len(reminders)} reminders.")

    # 4. Purge day_plans
    print("\n[4/7] Purging 'day_plans' collection in Firestore...")
    plans = list(client.collection("day_plans").stream())
    for p in plans:
        p.reference.delete()
    print(f"  ✅ Deleted {len(plans)} day plans.")

    # 5. Purge sessions and subcollections (chat history)
    print("\n[5/7] Purging 'sessions' and nested 'messages' in Firestore...")
    sessions = list(client.collection("sessions").stream())
    msg_count = 0
    for s in sessions:
        sub_msgs = client.collection("sessions").document(s.id).collection("messages").stream()
        for m in sub_msgs:
            m.reference.delete()
            msg_count += 1
        s.reference.delete()
    print(f"  ✅ Deleted {len(sessions)} sessions and {msg_count} nested messages.")

    # 6. Reset timetables to clean empty schedule (zero dummy blocks)
    print("\n[6/7] Resetting 'timetables' collection...")
    timetables = list(client.collection("timetables").stream())
    for tt in timetables:
        if tt.id in ("user_113746071667288617858", "default_user"):
            empty_table = {
                "user_id": tt.id,
                "updated_at": now_iso,
                "days": {
                    "monday": [],
                    "tuesday": [],
                    "wednesday": [],
                    "thursday": [],
                    "friday": [],
                    "saturday": [],
                    "sunday": []
                }
            }
            client.collection("timetables").document(tt.id).set(empty_table)
            print(f"  ✅ Reset {tt.id} timetable to empty schedule (0 blocks).")
        else:
            tt.reference.delete()
            print(f"  ✅ Deleted test timetable: {tt.id}")

    # 7. Check users collection - Preserve Apeksha M's credentials
    print("\n[7/7] Verifying user account & OAuth tokens...")
    users = list(client.collection("users").stream())
    for u in users:
        if u.id == "user_113746071667288617858":
            tokens = firestore_service.get_user_tokens(u.id)
            print(f"  🛡️ PRESERVED USER: {u.to_dict().get('name')} ({u.to_dict().get('email')})")
            print(f"  🛡️ OAuth Tokens intact: {tokens is not None}")
        elif u.id == "user_google_12345":
            u.reference.delete()
            print(f"  ✅ Removed temporary test user {u.id}.")

    # 8. Local cache files purge
    print("\n[Local Stores] Purging local JSON stores (.calendar_local.json, .gmail_local.json, .firestore_local.json)...")
    cal_file = PROJECT_ROOT / ".calendar_local.json"
    cal_file.write_text(json.dumps({"events": {}, "updated_at": now_iso}, indent=2), encoding="utf-8")
    calendar_mcp._events.clear()
    print("  ✅ .calendar_local.json cleared (0 mock events; real Google Calendar untouched).")

    gmail_file = PROJECT_ROOT / ".gmail_local.json"
    gmail_file.write_text(json.dumps({"drafts": {}, "updated_at": now_iso}, indent=2), encoding="utf-8")
    print("  ✅ .gmail_local.json cleared (0 mock drafts).")

    fs_local = PROJECT_ROOT / ".firestore_local.json"
    fs_local.write_text(json.dumps({
        "tasks": {},
        "notes": {},
        "reminders": {},
        "day_plans": {},
        "sessions": {},
        "timetables": {
            "default_user": {
                "user_id": "default_user",
                "updated_at": now_iso,
                "days": {d: [] for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
            }
        },
        "users": {}
    }, indent=2), encoding="utf-8")
    print("  ✅ .firestore_local.json reset to empty state.")

    print("\n🎉 WORKSPACE CLEANSED SUCCESSFULLY! ALL TABLES & STORES ARE NOW CLEAN & EMPTY.")

if __name__ == "__main__":
    purge_all()
