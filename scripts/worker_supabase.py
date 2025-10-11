# scripts/worker_supabase.py
import os, time, json, subprocess
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

AUDIO_EXTS = {".mp3", ".wav", ".m4a"}

load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_KEY  = os.environ["SUPABASE_SERVICE_KEY"]
BUCKET       = os.environ.get("W2C_BUCKET","w2c")
INCOMING     = os.environ.get("W2C_INCOMING_PREFIX","incoming/")
OUTPUTS      = os.environ.get("W2C_OUTPUTS_PREFIX","outputs/")

sb = create_client(SUPABASE_URL, SERVICE_KEY)

def list_incoming():
    # flat listing – adjust if you use folders
    files = sb.storage.from_(BUCKET).list(INCOMING, {"limit": 1000})
    # normalize to full path "incoming/<name>"
    out = []
    for o in files:
        name = o["name"]
        if name.endswith("/"):
            continue
        out.append(f"{INCOMING}{name}" if not name.startswith(INCOMING) else name)
    return out

def download(remote_path: str, to: Path):
    data = sb.storage.from_(BUCKET).download(remote_path)
    to.write_bytes(data)

def find_job_for(input_path: str):
    jobs = sb.storage.from_(BUCKET).list("jobs/", {"limit": 1000})
    for f in jobs:
        key = f"jobs/{f['name']}"
        try:
            blob = sb.storage.from_(BUCKET).download(key)
            job = json.loads(blob.decode("utf-8"))
            if job.get("input_path") == input_path:
                return key, job
        except Exception:
            pass
    return "", {}

def update_job(key: str, **chg):
    job = json.loads(sb.storage.from_(BUCKET).download(key).decode("utf-8"))
    job.update(chg)
    sb.storage.from_(BUCKET).upload(
        key,
        json.dumps(job).encode("utf-8"),
        {"content-type": "application/json", "x-upsert": "true"},
    )

def signed_url(path: str, secs=3600*24*30):
    return sb.storage.from_(BUCKET).create_signed_url(path, secs)["signedURL"]

def upload(local: Path, remote: str, ctype: str):
    sb.storage.from_(BUCKET).upload(
        remote, local.read_bytes(),
        {"content-type": ctype, "x-upsert": "true"}
    )
    return signed_url(remote)

def process_one(remote_in: str):
    name = Path(remote_in).name
    # skip non-audio (prevents .emptyFolderPlaceholder crash)
    if Path(name).suffix.lower() not in AUDIO_EXTS:
        print(f"↷ Skipping non-audio {name}")
        return

    inputs = Path("inputs"); inputs.mkdir(exist_ok=True)
    local_in = inputs / name
    print("↓", remote_in)
    download(remote_in, local_in)

    job_key, _ = find_job_for(remote_in)
    if job_key:
        update_job(job_key, status="running", started_at=int(time.time()))

    # full W2C pipeline
    subprocess.run(["scripts/run_one.sh", str(local_in), "Odin :: Foundations", "small"], check=True)
    subprocess.run(["poetry","run","python","scripts/make_decks.py","--mode","ds"], check=True)

    # upload artifacts (use one canonical ZIP name)
    slug = Path(name).stem.replace(" ", "_")
    outdir = f"{OUTPUTS}{slug}/"
    links = {}

    def up(rel, loc, ctype):
        p = Path(loc)
        if p.exists():
            links[rel] = upload(p, f"{outdir}{rel}", ctype)

    up("notes.html", "outputs/notes.html", "text/html")
    up("notes.pdf",  "outputs/notes.pdf",  "application/pdf")
    up("deck.csv",   "outputs/deck.csv",   "text/csv")
    up("deck.apkg",  "outputs/deck.apkg",  "application/octet-stream")
    up("bundle.zip", "dist/lecture_easyread.zip", "application/zip")  # keep underscore; see #4

    if job_key:
        update_job(job_key, status="complete", completed_at=int(time.time()), outputs=links)
    print("✓", name)

def main():
    seen = set()
    print("Worker: polling Supabase… (Ctrl+C to stop)")
    while True:
        try:
            for path in list_incoming():
                if path in seen:
                    continue
                process_one(path)
                seen.add(path)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("WARN:", e)
            time.sleep(2)
        time.sleep(3)

if __name__ == "__main__":
    main()
