from fastapi import FastAPI
from app.api.routes import router
from app.workers.loop import start_loop, stop_loop

app = FastAPI()
app.include_router(router)

@app.on_event("startup")
async def _s():
    await start_loop()

@app.on_event("shutdown")
async def _x():
    await stop_loop()