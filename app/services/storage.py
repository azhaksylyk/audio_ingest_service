from pathlib import Path
from app.core.config import settings

def upload_dir(upload_id: str) -> Path:
    p = Path(settings.tmp_dir) / upload_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def chunk_path(upload_id: str, idx: int) -> Path:
    return upload_dir(upload_id) / f"{idx}.bin"

def final_audio_path(audio_id: str, filename: str) -> Path:
    p = Path(settings.storage_dir) / audio_id
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.with_suffix(Path(filename).suffix or ".wav")