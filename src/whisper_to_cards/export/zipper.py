from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import json
import hashlib
import time
import zipfile

REQUIRED = ["notes.html"]  # we’ll include notes.pdf if it exists


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _gather(outdir: Path, include_pdf: bool = True) -> List[Path]:
    keep: List[Path] = []
    # required
    for name in ["notes.html"]:
        p = outdir / name
        if not p.exists():
            raise FileNotFoundError(f"Missing {name} in {outdir}")
        keep.append(p)

    # optional
    if include_pdf:
        p = outdir / "notes.pdf"
        if p.exists():
            keep.append(p)

    for name in ["structured.json", "sections.json", "transcript.json"]:
        p = outdir / name
        if p.exists():
            keep.append(p)

    for dname in ["audio", "fonts"]:
        d = outdir / dname
        if d.exists():
            for p in d.rglob("*"):
                if p.is_file():
                    keep.append(p)
    return keep


def _manifest(files: List[Path], outdir: Path) -> Dict:
    items = []
    for p in files:
        rel = str(p.relative_to(outdir).as_posix())
        items.append(
            {
                "path": rel,
                "size": p.stat().st_size,
                "sha256": _sha256(p),
            }
        )
    return {
        "generated_at": int(time.time()),
        "root": str(outdir),
        "files": items,
        "version": 1,
    }


def make_zip(outdir: Path, zip_path: Path, include_pdf: bool = True) -> Path:
    outdir = outdir.resolve()
    files = _gather(outdir, include_pdf=include_pdf)
    mani = _manifest(files, outdir)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # add files under their relative paths
        for p in files:
            z.write(p, arcname=str(p.relative_to(outdir).as_posix()))
        # include a manifest for traceability
        z.writestr("manifest.json", json.dumps(mani, indent=2))

        # small landing README inside the zip
        readme = (
            "# Whisper-to-Cards bundle\n\n"
            "Open **notes.html** in a browser (works offline).\n\n"
            "- **notes.pdf** is included if we could generate it.\n"
            "- **audio/** has per-section audio if you created it.\n"
            "- **fonts/** are embedded so the page renders offline.\n"
        )
        z.writestr("README.txt", readme)

    return zip_path
