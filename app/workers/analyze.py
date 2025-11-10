import numpy as np, soundfile as sf, asyncio, uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from app.db import models

def features(sig: np.ndarray, sr: int, win_ms: int = 30, hop_ms: int = 10):
    w = int(sr*win_ms/1000)
    h = int(sr*hop_ms/1000)
    n = 1 + max(0, (len(sig)-w)//h)
    rms = []
    zcr = []
    starts = []
    ends = []
    for i in range(n):
        s = i*h
        e = s+w
        x = sig[s:e]
        if len(x)==0:
            continue
        v = float(np.sqrt(np.mean(x.astype(np.float64)**2)))
        c = float(np.mean(np.abs(np.diff(np.sign(x))))/2.0)
        rms.append(v)
        zcr.append(c)
        starts.append(int(1000*s/sr))
        ends.append(int(1000*min(e,len(sig))/sr))
    return starts, ends, rms, zcr

def vad_threshold(rms: list[float]) -> float:
    if not rms:
        return 0.0
    m = float(np.median(rms))
    return max(m*2.0, 1e-6)

async def analyze_audio(db: AsyncSession, job_id: int, upload_id: uuid.UUID, audio_id: uuid.UUID, path: str):
    try:
        data, sr = sf.read(path, always_2d=False)
        if data.ndim==2:
            data = data.mean(axis=1)
        starts, ends, rms, zcr = await asyncio.to_thread(features, data, sr)
        thr = vad_threshold(rms)
        items = []
        for s,e,rv,zv in zip(starts, ends, rms, zcr):
            if rv >= thr:
                items.append({"audio_id": audio_id, "start_ms": s, "end_ms": e, "rms": rv, "zcr": zv, "transcript": "beep"})
        await db.execute(update(models.AudioFile).where(models.AudioFile.id==audio_id).values(sample_rate=sr, channels=1, duration_s=float(len(data)/sr), format="wav"))
        if items:
            await db.execute(insert(models.Segment), items)
        await db.execute(update(models.Job).where(models.Job.id==job_id).values(status="done"))
        await db.execute(update(models.Upload).where(models.Upload.id==upload_id).values(status="ready"))
        await db.commit()
    except Exception as e:
        await db.execute(update(models.Job).where(models.Job.id==job_id).values(status="failed", last_error=str(e), attempts=models.Job.attempts+1))
        await db.commit()