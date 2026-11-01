import asyncio
import httpx
from app.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        print("STATUS:", response.status_code)
        print("BODY:", response.text)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "nexus-api"
        print("HEALTH_CHECK_PASSED")


if __name__ == "__main__":
    asyncio.run(main())

