import os, time, subprocess, urllib.parse, psycopg

def to_sync_dsn(url: str) -> str:
    u = urllib.parse.urlsplit(url)
    return f"postgresql://{u.username}:{u.password}@{u.hostname}:{u.port}{u.path}"

def wait_for_postgres(dsn: str, timeout: int = 600):
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            with psycopg.connect(dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("select 1")
                    cur.fetchone()
                    cur.execute("select pg_is_in_recovery()")
                    cur.fetchone()
            return
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"Postgres not ready after {timeout}s: {last_err}")

def run_with_retries(cmd: list[str], retries: int = 30, delay: float = 1.0):
    for i in range(retries):
        try:
            subprocess.check_call(cmd)
            return
        except subprocess.CalledProcessError:
            time.sleep(min(delay * (2 ** i), 10.0))
    subprocess.check_call(cmd)

dsn = os.environ.get("DATABASE_SYNC_URL") or to_sync_dsn(os.environ.get("DATABASE_URL", "postgresql://app:app@db:5432/app"))
wait_for_postgres(dsn)
run_with_retries(["alembic", "upgrade", "head"])
subprocess.check_call(["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])