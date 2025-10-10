from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil, time

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

INPUTS = Path("inputs"); INPUTS.mkdir(exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    safe = "".join(c for c in file.filename if c.isalnum() or c in " ._-").strip()
    dest = INPUTS / f"{int(time.time())}_{safe}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)   # <-- actually save the bytes
    return JSONResponse({"ok": True, "path": str(dest.name)})
