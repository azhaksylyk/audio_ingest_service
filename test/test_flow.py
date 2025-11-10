import pytest
import asyncio
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_full_flow_verbose():
    print("\n=== STEP 1: Start upload ===")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        # Create a fake audio payload (8 bytes)
        data = b"\x00" * 8
        start_payload = {"filename": "t.wav", "content_type": "audio/wav", "size_bytes": len(data)}
        r = await c.post("/ingest/start", json=start_payload)
        print("Response:", r.text)
        r.raise_for_status()
        upload_id = r.json()["upload_id"]

        print("\n=== STEP 2: Send chunk ===")
        headers = {
            "X-Upload-Id": upload_id,
            "X-Chunk-Index": "0",
            "Content-Range": f"bytes 0-{len(data)-1}/{len(data)}",
            "Content-Length": str(len(data)),
        }
        r = await c.post("/ingest/chunk", headers=headers, content=data)
        print("Response:", r.text)
        r.raise_for_status()

        print("\n=== STEP 3: Complete upload ===")
        r = await c.post("/ingest/complete", headers={"X-Upload-Id": upload_id})
        print("Response:", r.text)
        r.raise_for_status()

        print("\n=== STEP 4: Wait for analysis job ===")
        await asyncio.sleep(2)

        print("\n=== STEP 5: Retrieve audio list ===")
        # Find latest audio_id directly from DB or storage directory
        import os
        files = os.listdir("/data/storage")
        assert files, "No stitched audio found in /data/storage"
        audio_id = files[-1].replace(".wav", "")
        print("Found audio_id:", audio_id)

        print("\n=== STEP 6: Fetch metadata ===")
        r = await c.get(f"/audio/{audio_id}")
        print("Response:", r.text)
        r.raise_for_status()
        data = r.json()
        assert data["status"] in ("processing", "ready")

        print("\n=== STEP 7: Fetch segments ===")
        r = await c.get(f"/audio/{audio_id}/segments?limit=10&offset=0")
        print("Response:", r.text)
        r.raise_for_status()

        print("\n=== STEP 8: Fetch stats ===")
        r = await c.get("/stats", params={"from_": "2020-01-01T00:00:00Z", "to": "2030-01-01T00:00:00Z"})
        print("Response:", r.text)
        r.raise_for_status()

        print("\n✅ TEST PASSED SUCCESSFULLY ✅")