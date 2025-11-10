import asyncio, uuid
from sqlalchemy import text, select, update
from app.db.session import AsyncSessionLocal
from app.db import models
from app.workers.analyze import analyze_audio

async def poll():
    while True:
        async with AsyncSessionLocal() as db:
            job_row = None
            # Explicitly start and commit each iteration
            async with db.begin():
                res = await db.execute(
                    text("""
                        SELECT id, upload_id, payload
                        FROM jobs
                        WHERE type='analyze' AND status='queued'
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    """)
                )
                job_row = res.first()
                if job_row:
                    await db.execute(
                        update(models.Job)
                        .where(models.Job.id == job_row.id)
                        .values(status="in_progress", attempts=models.Job.attempts + 1)
                    )
            # <-- db.begin() auto-commits here, so no open transaction

            if job_row:
                try:
                    audio_id = uuid.UUID(job_row.payload["audio_id"])
                    af = (
                        await db.execute(
                            select(models.AudioFile).where(models.AudioFile.id == audio_id)
                        )
                    ).scalar_one()
                    await analyze_audio(db, job_row.id, job_row.upload_id, audio_id, af.path)
                except Exception as e:
                    print(f"[Worker] Error processing job {job_row.id}: {e}")
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