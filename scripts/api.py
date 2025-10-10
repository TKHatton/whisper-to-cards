from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
import os, time, json, uuid
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
ANON_KEY      = os.environ["SUPABASE_ANON_KEY"]       # not used on server, but okay
SERVICE_KEY   = os.environ["SUPABASE_SERVICE_KEY"]
BUCKET        = os.environ.get("W2C_BUCKET", "w2c")
INCOMING      = os.environ.get("W2C_INCOMING_PREFIX", "incoming/")
OUTPUTS       = os.environ.get("W2C_OUTPUTS_PREFIX",  "outputs/")

sb: Client = create_client(SUPABASE_URL, SERVICE_KEY)  # service key so we can sign uploads & manage jobs

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SignReq(BaseModel):
    filename: str
    content_type: str = "audio/mpeg"

def safe_name(name: str) -> str:
    base = "".join(c for c in name if c.isalnum() or c in " ._-").strip()
    return base or f"upload_{int(time.time())}.bin"

def job_key(job_id: str) -> str:
    return f"jobs/{job_id}.json"

@app.post("/sign-upload")
def sign_upload(body: SignReq):
    """
    Create a signed URL so the browser can PUT the file directly to Supabase Storage.
    """
    fn = safe_name(body.filename)
    path = f"{INCOMING}{int(time.time())}_{fn}"
    # Signed upload URL is valid for 60 mins (3600s)
    res = sb.storage.from_(BUCKET).create_signed_upload_url(path)
    signed_url = res["signedUrl"]    # e.g. /storage/v1/object/sign/...
    full_url   = f"{SUPABASE_URL}{signed_url}"

    # Create a job record (status=pending)
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "input_path": path,
        "status": "pending",
        "created_at": int(time.time()),
        "outputs": {}
    }
    sb.storage.from_(BUCKET).upload(job_key(job_id), json.dumps(job).encode("utf-8"), {"content-type": "application/json", "x-upsert": "true"})

    return JSONResponse({"ok": True, "job_id": job_id, "upload_url": full_url, "storage_path": path})

@app.get("/status")
def status(job_id: str):
    """Return the current job JSON."""
    try:
        data = sb.storage.from_(BUCKET).download(job_key(job_id))
        job = json.loads(data.decode("utf-8"))
        return job
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=404)
