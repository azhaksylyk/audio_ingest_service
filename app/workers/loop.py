import asyncio, uuid
from sqlalchemy import text, select, update
from app.db.session import AsyncSessionLocal
from app.db import models
from app.workers.analyze import analyze_audio

async def poll():
    while True:
        async with AsyncSessionLocal() as db:
            await db.execute(text("begin"))
            row = await db.execute(text("select id, upload_id, payload from jobs where type='analyze' and status='queued' for update skip locked limit 1"))
            r = row.first()
            if r:
                await db.execute(update(models.Job).where(models.Job.id==r.id).values(status="in_progress", attempts=models.Job.attempts+1))
                await db.commit()
                audio_id = uuid.UUID(r.payload["audio_id"])
                af = (await db.execute(select(models.AudioFile).where(models.AudioFile.id==audio_id))).scalar_one()
                await analyze_audio(db, r.id, r.upload_id, audio_id, af.path)
            else:
                await db.rollback()
        await asyncio.sleep(1)

task = None

async def start_loop():
    global task
    if task is None:
        task = asyncio.create_task(poll())

async def stop_loop():
    global task
    if task:
        task.cancel()
        task = None