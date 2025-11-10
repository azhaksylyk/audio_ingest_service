import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, Body, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.db.session import get_session
from app.db import models
from app.api.schemas import *
from app.services.ingest import start_upload, receive_chunk, complete_upload

router = APIRouter()

def _parse_dt(s: str) -> datetime:
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(timezone.utc)

@router.post("/ingest/start", response_model=StartOut)
async def ingest_start(payload: StartIn, db: AsyncSession = Depends(get_session)):
    uid = await start_upload(db, payload.filename, payload.content_type, payload.size_bytes)
    return {"upload_id": uid, "status": "receiving"}

@router.post("/ingest/chunk", response_model=ChunkOut)
async def ingest_chunk(request: Request, db: AsyncSession = Depends(get_session), x_upload_id: uuid.UUID = Header(..., alias="X-Upload-Id"), x_chunk_index: int = Header(..., alias="X-Chunk-Index"), content_range: str = Header(..., alias="Content-Range"), content_length: int = Header(..., alias="Content-Length"), x_chunk_sha256: str | None = Header(None, alias="X-Chunk-SHA256")):
    body = await request.body()
    try:
        received, total = await receive_chunk(db, x_upload_id, x_chunk_index, content_range, content_length, body, x_chunk_sha256)
        return {"received_bytes": received, "expected_total": total}
    except ValueError as e:
        msg = str(e)
        if msg in {"range_length_mismatch", "range_gap", "wrong_total", "invalid"}:
            raise HTTPException(status_code=400, detail={"message": msg})
        raise

@router.post("/ingest/complete", response_model=CompleteOut)
async def ingest_complete(db: AsyncSession = Depends(get_session), x_upload_id: uuid.UUID = Header(..., alias="X-Upload-Id"), body: dict | None = Body(None)):
    checksum = None
    if body and "checksum_sha256" in body:
        checksum = body["checksum_sha256"]
    try:
        upload_id, audio_id = await complete_upload(db, x_upload_id, checksum)
        return {"upload_id": upload_id, "job": "analyze", "status": "queued"}
    except ValueError as e:
        msg = str(e)
        if msg in {"no_chunks","range_gap","wrong_total","checksum_mismatch"}:
            raise HTTPException(status_code=409, detail={"message": msg})
        raise

@router.get("/audio/{audio_id}", response_model=AudioMetaOut)
async def get_audio(audio_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    af = (await db.execute(select(models.AudioFile).where(models.AudioFile.id==audio_id))).scalar_one_or_none()
    if not af:
        raise HTTPException(status_code=404, detail={"message":"not_found"})
    up = (await db.execute(select(models.Upload).where(models.Upload.id==af.upload_id))).scalar_one()
    return {"audio_id": af.id, "upload_id": af.upload_id, "status": up.status, "sample_rate": af.sample_rate, "channels": af.channels, "duration_s": float(af.duration_s) if af.duration_s else None, "format": af.format}

@router.get("/audio/{audio_id}/segments", response_model=SegmentList)
async def list_segments(audio_id: uuid.UUID, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_session)):
    total = (await db.execute(select(func.count()).select_from(models.Segment).where(models.Segment.audio_id==audio_id))).scalar()
    rows = (await db.execute(select(models.Segment).where(models.Segment.audio_id==audio_id).order_by(models.Segment.start_ms).limit(limit).offset(offset))).scalars().all()
    items = [{"start_ms": r.start_ms, "end_ms": r.end_ms, "rms": r.rms, "zcr": r.zcr, "transcript": r.transcript} for r in rows]
    return {"items": items, "total": int(total or 0), "limit": limit, "offset": offset}

@router.get("/stats", response_model=StatsOut)
async def stats(from_: str, to: str, db: AsyncSession = Depends(get_session)):
    f_dt = _parse_dt(from_)
    t_dt = _parse_dt(to)
    q = text("""
        select date_trunc('hour', created_at) as hour,
               sum((end_ms - start_ms)/1000.0) as voice_duration_s,
               percentile_cont(0.95) within group (order by rms) as p95_rms,
               count(*) as segments
        from segments
        where created_at >= :f and created_at < :t
        group by 1
        order by 1
    """)
    rows = (await db.execute(q, {"f": f_dt, "t": t_dt})).all()
    buckets = [{"hour": r.hour.replace(minute=0, second=0, microsecond=0).isoformat().replace("+00:00","Z"), "voice_duration_s": float(r.voice_duration_s or 0.0), "p95_rms": float(r.p95_rms) if r.p95_rms is not None else None, "segments": int(r.segments)} for r in rows]
    return {"buckets": buckets}