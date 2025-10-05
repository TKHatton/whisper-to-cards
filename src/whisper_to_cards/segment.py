from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple
import json
import re


@dataclass
class Section:
    id: str
    title: str
    start_idx: int
    end_idx: int
    text: str
    timestamps: List[Tuple[float, float]]


def _load_transcript(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _should_break(prev_text: str, curr_text: str) -> bool:
    cues = (
        r"^so[, ]",
        r"^in (conclusion|summary)",
        r"^next[, ]",
        r"^now[, ]",
        r"^okay[, ]",
        r"^let'?s",
    )
    if any(re.match(pat, curr_text.lower()) for pat in cues):
        return True
    if prev_text.endswith((".", "?", "!")) and curr_text[:1].isupper():
        return True
    return False


def segment_transcript(
    transcript_path: Path, max_chars: int = 1200, max_segments: int = 200
) -> List[Section]:
    data = _load_transcript(transcript_path)
    segs = data["segments"]

    sections: List[Section] = []
    buff_text, buff_ts = [], []
    start_idx = 0
    char_count = 0

    def flush(end_idx: int):
        nonlocal start_idx, buff_text, buff_ts, char_count, sections
        if not buff_text:
            return
        text = " ".join(buff_text).strip()
        title = (
            re.split(r"[.!?]", text, maxsplit=1)[0][:70].strip()
            or f"Section {len(sections)+1}"
        )
        sec = Section(
            id=f"sec_{len(sections)+1:02d}",
            title=title,
            start_idx=start_idx,
            end_idx=end_idx,
            text=text,
            timestamps=buff_ts[:],
        )
        sections.append(sec)
        buff_text, buff_ts = [], []
        char_count = 0

    for i, s in enumerate(segs[:max_segments]):
        t = (s.get("text") or "").strip()
        if not t:
            continue
        if buff_text and (char_count >= max_chars or _should_break(buff_text[-1], t)):
            flush(i - 1)
            start_idx = i
        buff_text.append(t)
        buff_ts.append((float(s["start"]), float(s["end"])))
        char_count += len(t)

    flush(len(segs[:max_segments]) - 1)

    # merge very short trailing sections
    merged: List[Section] = []
    for sec in sections:
        if merged and len(sec.text) < 200:
            prev = merged[-1]
            prev.text = (prev.text + " " + sec.text).strip()
            prev.end_idx = sec.end_idx
            prev.timestamps.extend(sec.timestamps)
        else:
            merged.append(sec)
    return merged


def write_sections(
    sections: List[Section], out_path: Path, meta: dict | None = None
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta or {}, "sections": [asdict(s) for s in sections]}
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path
