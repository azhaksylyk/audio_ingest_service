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

```

## Run tests

### Step 1. Get file size
```bash
SIZE=$(stat -f%z test.wav 2>/dev/null || stat -c%s test.wav)
echo $SIZE
```
### Step 2. Start upload
```bash
curl -s -X POST http://localhost:8000/ingest/start \
  -H 'Content-Type: application/json' \
  -d '{"filename":"test.wav","content_type":"audio/wav","size_bytes":'"$SIZE"'}'
```
### Step 3. Set upload ID
Use UPLOAD_ID from Step 2.
```bash
UPLOAD_ID=<paste_upload_id_here>
```
example: UPLOAD_ID=79451b97-2f4a-4a5c-bf1d-e98aabd7a995
### Step 4. Upload file chunk
```bash
curl -s -X POST http://localhost:8000/ingest/chunk \
  -H "X-Upload-Id: $UPLOAD_ID" \
  -H "X-Chunk-Index: 0" \
  -H "Content-Range: bytes 0-$((SIZE-1))/$SIZE" \
  -H "Content-Length: $SIZE" \
  --data-binary @test.wav
```
Expected:
{"received_bytes": SIZE, "expected_total": SIZE}
### Step 5. Complete upload
```bash
curl -s -X POST http://localhost:8000/ingest/complete \
  -H "X-Upload-Id: $UPLOAD_ID"
```
Expected:
{"job":"analyze","status":"queued"}

### Step 6. Get audio ID
```bash
docker-compose exec -T app sh -lc 'ls -1 /data/storage | tail -n1'
```
Copy the UUID (without .wav).

### Step 7.
```bash
AUDIO_ID=<paste_audio_id_here>
```
exmaple: AUDIO_ID=8858d321-604a-4923-993c-e20f862985c7

### Step 8. Fetch metadata
```bash
curl -s "http://localhost:8000/audio/$AUDIO_ID" | jq
```

### Step 9. Fetch segments
```bash
curl -s "http://localhost:8000/audio/$AUDIO_ID/segments?limit=100&offset=0" | jq
```

### Step 10. Fetch stats
```bash
curl -Gs http://localhost:8000/stats \
  --data-urlencode "from_=2020-01-01T00:00:00Z" \
  --data-urlencode "to=2030-01-01T00:00:00Z" | jq
```

### Step 11. Copy result WAV
```bash
docker cp $(docker-compose ps -q app):/data/storage/${AUDIO_ID}.wav ./out.wav
```


## Run Automatic test
```bash
docker cp $(docker-compose ps -q app):/data/storage/${AUDIO_ID}.wav ./out.wav
```

## Repository
https://github.com/azhaksylyk/audio_ingest_service
