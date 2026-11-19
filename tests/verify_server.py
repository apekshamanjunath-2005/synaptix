"""
Server Verification Script
Spawns uvicorn in a background thread, queries /api/health and /, then shuts down cleanly.
"""

import sys
import time
import threading
import urllib.request
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from app.main import app


class ServerThread(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8888):
        super().__init__(daemon=True)
        config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
        self.server = uvicorn.Server(config=config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def verify_server():
    server = ServerThread(port=8888)
    server.start()

    # Wait for server to bind
    time.sleep(1.5)

    try:
        # Test 1: Health endpoint
        req = urllib.request.Request("http://127.0.0.1:8888/api/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            print("✅ /api/health returned 200 OK:")
            print(f"   Service: {data['service']}")
            print(f"   Status: {data['status']}")
            print(f"   Uptime: {data['uptime_seconds']}s")
            print(f"   Python: {data['runtime']['python_version']}")
            print(f"   Budget tier: {data['budget_telemetry']['budget_tier']}")

        # Test 2: Frontend index
        req_index = urllib.request.Request("http://127.0.0.1:8888/")
        with urllib.request.urlopen(req_index, timeout=5) as resp:
            assert resp.status == 200
            html = resp.read().decode()
            assert "Synaptix" in html
            print("✅ / returned 200 OK: Frontend dashboard HTML loaded successfully")

        # Test 3: Static files (CSS)
        req_css = urllib.request.Request("http://127.0.0.1:8888/static/css/styles.css")
        with urllib.request.urlopen(req_css, timeout=5) as resp:
            assert resp.status == 200
            css = resp.read().decode()
            assert "--accent-primary" in css
            print("✅ /static/css/styles.css returned 200 OK")

        # Test 4: Static files (JS)
        req_js = urllib.request.Request("http://127.0.0.1:8888/static/js/app.js")
        with urllib.request.urlopen(req_js, timeout=5) as resp:
            assert resp.status == 200
            js = resp.read().decode()
            assert "Synaptix" in js
            print("✅ /static/js/app.js returned 200 OK")

        print("\n🎉 ALL SERVER VERIFICATION CHECKS PASSED SUCCESSFULLY!")

    finally:
        server.stop()


if __name__ == "__main__":
    verify_server()
