import pytest, asyncio
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_full_flow():
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        r = await c.post("/ingest/start", json={"filename":"t.wav","content_type":"audio/wav","size_bytes":8})
        uid = r.json()["upload_id"]
        await c.post("/ingest/chunk", headers={"X-Upload-Id":uid,"X-Chunk-Index":"0","Content-Range":"bytes 0-7/8","Content-Length":"8"}, content=b"\x00"*8)
        await c.post("/ingest/complete", headers={"X-Upload-Id":uid})
        await asyncio.sleep(1)