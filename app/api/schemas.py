from pydantic import BaseModel
from uuid import UUID

class StartIn(BaseModel):
    filename: str
    content_type: str
    size_bytes: int

class StartOut(BaseModel):
    upload_id: UUID
    status: str

class ChunkOut(BaseModel):
    received_bytes: int
    expected_total: int

class CompleteOut(BaseModel):
    upload_id: UUID
    job: str
    status: str

class AudioMetaOut(BaseModel):
    audio_id: UUID
    upload_id: UUID
    status: str
    sample_rate: int | None = None
    channels: int | None = None
    duration_s: float | None = None
    format: str | None = None

class SegmentItem(BaseModel):
    start_ms: int
    end_ms: int
    rms: float | None = None
    zcr: float | None = None
    transcript: str | None = None

class SegmentList(BaseModel):
    items: list[SegmentItem]
    total: int
    limit: int
    offset: int

class StatsBucket(BaseModel):
    hour: str
    voice_duration_s: float
    p95_rms: float | None = None
    segments: int

class StatsOut(BaseModel):
    buckets: list[StatsBucket]