import pytest
from app.db.session import AsyncSessionLocal
from app.services.ingest import start_upload, receive_chunk

@pytest.mark.asyncio
async def test_idempotent():
    async with AsyncSessionLocal() as db:
        uid = await start_upload(db, "x.wav", "audio/wav", 10)
        b = b"0123456789"
        r1 = await receive_chunk(db, uid, 0, "bytes 0-9/10", 10, b, None)
        r2 = await receive_chunk(db, uid, 0, "bytes 0-9/10", 10, b, None)
        assert r1[0]==10 and r2[0]==10