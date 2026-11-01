import threading
import time
import httpx
import uvicorn
from app.main import app


def run_live_probe():
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )
    server = uvicorn.Server(config=config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for socket to bind
    for _ in range(20):
        if server.started:
            break
        time.sleep(0.2)

    try:
        response = httpx.get("http://127.0.0.1:8000/api/v1/health", timeout=5.0)
        print("LIVE_HTTP_STATUS:", response.status_code)
        print("LIVE_HTTP_RESPONSE:", response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "nexus-api"
        print("LIVE_SERVER_VERIFICATION_PASSED")
    finally:
        server.should_exit = True
        thread.join(timeout=3.0)


if __name__ == "__main__":
    run_live_probe()

