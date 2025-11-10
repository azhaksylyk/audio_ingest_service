# Audio Ingest Service

A lightweight service for chunked audio uploads, processing, and analysis built with **FastAPI**, **PostgreSQL**, and **Docker**.

## Features
- Chunked upload workflow (`/ingest/start`, `/ingest/chunk`, `/ingest/complete`)
- Post-upload file stitching and checksum validation
- Background audio analysis (RMS, ZCR, simple VAD)
- REST APIs for metadata, segments, and hourly stats
- Dockerized with Alembic migrations and unit tests

## Quick Start

### 1. Clean and rebuild
```bash
docker-compose down --rmi all -v
docker system prune -af
docker volume prune -f
```

### 2. Start the stack
```bash
docker-compose up --build -d
docker-compose logs -f app
```
Wait for:
```bash
Uvicorn running on http://0.0.0.0:8000
```

### 3. Open docs
http://localhost:8000/docs

## Manual Test Example
```bash
# create 1-second wav file
python3 - <<'PY'
import numpy as np, soundfile as sf
sr=16000
t=np.arange(sr)/sr
x=0.2*np.sin(2*np.pi*1000*t).astype(np.float32)
sf.write('test.wav', x, sr)
PY

# upload workflow
SIZE=$(stat -f%z test.wav 2>/dev/null || stat -c%s test.wav)
UID=$(curl -s -X POST http://localhost:8000/ingest/start -H 'Content-Type: application/json' -d '{"filename":"test.wav","content_type":"audio/wav","size_bytes":'$SIZE'}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["upload_id"])')
curl -s -X POST http://localhost:8000/ingest/chunk -H "X-Upload-Id: $UID" -H "X-Chunk-Index: 0" -H "Content-Range: bytes 0-$((SIZE-1))/$SIZE" -H "Content-Length: $SIZE" --data-binary @test.wav >/dev/null
curl -s -X POST http://localhost:8000/ingest/complete -H "X-Upload-Id: $UID"

# find and inspect audio id
AID=$(docker-compose exec -T app sh -lc 'ls -1 /data/storage | tail -n1' | sed 's/\\.wav$//')
curl -s "http://localhost:8000/audio/$AID" | jq
curl -s "http://localhost:8000/audio/$AID/segments?limit=100&offset=0" | jq
```

## Run tests
```bash
docker-compose exec app pytest -q
```

## Repository
https://github.com/azhaksylyk/audio_ingest_service
