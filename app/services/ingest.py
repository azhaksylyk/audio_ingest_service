import uuid, hashlib, os
from sqlalchemy import select, func, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models
from app.services.utils import parse_content_range
from app.services.storage import chunk_path, final_audio_path

async def start_upload(db: AsyncSession, filename: str, content_type: str, size_bytes: int) -> uuid.UUID:
    up = models.Upload(id=uuid.uuid4(), filename=filename, content_type=content_type, size_bytes=size_bytes, status="receiving")
    db.add(up)
    await db.commit()
    return up.id

async def receive_chunk(db: AsyncSession, upload_id: uuid.UUID, chunk_index: int, content_range: str, content_length: int, body: bytes, sha256: str | None) -> tuple[int,int]:
    s, e, total = parse_content_range(content_range)
    if e - s + 1 != content_length:
        raise ValueError("range_length_mismatch")
    exists = await db.execute(select(models.UploadChunk).where(models.UploadChunk.upload_id==upload_id, models.UploadChunk.chunk_index==chunk_index))
    if exists.scalar():
        q = await db.execute(select(func.coalesce(func.sum(models.UploadChunk.size_bytes),0)).where(models.UploadChunk.upload_id==upload_id))
        received = int(q.scalar() or 0)
        return received, total
    p = chunk_path(str(upload_id), chunk_index)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.write(body)
    rec = models.UploadChunk(upload_id=upload_id, chunk_index=chunk_index, range_start=s, range_end=e, size_bytes=content_length, sha256=sha256)
    db.add(rec)
    await db.commit()
    q = await db.execute(select(func.coalesce(func.sum(models.UploadChunk.size_bytes),0)).where(models.UploadChunk.upload_id==upload_id))
    received = int(q.scalar() or 0)
    return received, total

async def complete_upload(db: AsyncSession, upload_id: uuid.UUID, checksum: str | None) -> tuple[uuid.UUID, uuid.UUID]:
    up = (await db.execute(select(models.Upload).where(models.Upload.id==upload_id))).scalar_one()
    rows = (await db.execute(select(models.UploadChunk).where(models.UploadChunk.upload_id==upload_id).order_by(models.UploadChunk.chunk_index))).scalars().all()
    if not rows:
        raise ValueError("no_chunks")
    total = rows[-1].range_end + 1
    expected = up.size_bytes or total
    coverage = 0
    for r in rows:
        if r.range_start != coverage:
            raise ValueError("range_gap")
        coverage = r.range_end + 1
    if coverage != expected:
        raise ValueError("wrong_total")
    audio_id = uuid.uuid4()
    dst = final_audio_path(str(audio_id), up.filename)
    with open(dst, "wb") as out:
        for r in rows:
            with open(chunk_path(str(upload_id), r.chunk_index), "rb") as f:
                out.write(f.read())
    if checksum:
        h = hashlib.sha256()
        with open(dst, "rb") as f:
            for b in iter(lambda: f.read(1048576), b""):
                h.update(b)
        if h.hexdigest() != checksum:
            os.remove(dst)
            raise ValueError("checksum_mismatch")
    af = models.AudioFile(id=audio_id, upload_id=upload_id, path=str(dst))
    db.add(af)
    await db.execute(update(models.Upload).where(models.Upload.id==upload_id).values(status="processing", completed_at=func.now()))
    try:
        await db.execute(insert(models.Job).values(upload_id=upload_id, type="analyze", status="queued", payload={"audio_id": str(audio_id)}))
    except Exception:
        pass
    await db.commit()
    return upload_id, audio_id