from __future__ import annotations
from pathlib import Path
import zipfile


def _add_file(z: zipfile.ZipFile, src: Path, arcname: str | None = None):
    if src.exists():
        z.write(src, arcname or src.name)


def _add_tree(z: zipfile.ZipFile, root: Path, arcroot: str):
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(root)
            z.write(p, f"{arcroot}/{rel.as_posix()}")


def make_bundle(
    outputs_dir: Path,
    bundle_name: str = "w2c_bundle.zip",
    include_pdf: bool = True,
) -> Path:
    """
    Create a distributable zip with notes, audio, anki deck, and structured JSON.
    Returns path to the created zip.
    """
    outputs_dir.mkdir(parents=True, exist_ok=True)
    zip_path = outputs_dir / bundle_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        _add_file(z, outputs_dir / "notes.html")
        if include_pdf:
            _add_file(z, outputs_dir / "notes.pdf")
        _add_file(z, outputs_dir / "structured.json")
        _add_file(z, outputs_dir / "deck.csv")
        _add_file(z, outputs_dir / "deck.apkg")
        _add_tree(z, outputs_dir / "audio", "audio")
    return zip_path
