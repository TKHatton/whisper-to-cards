from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import json

from faster_whisper import WhisperModel

@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None  # reserved for diarization later

@dataclass
class Transcript:
    meta: dict
    segments: List[Segment]

    def to_dict(self) -> dict:
        return {
            "meta": self.meta,
            "segments": [asdict(s) for s in self.segments],
        }

def transcribe_audio(
    input_path: Path,
    model_size: str = "small",
    language: Optional[str] = None,
    device: str = "auto",       # "cpu" | "cuda" | "auto"
    compute_type: str = "auto", # "int8" | "float16" | "auto" | ...
) -> Transcript:
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments_iter, _info = model.transcribe(
        str(input_path),
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
    )
    segments = [
        Segment(start=float(s.start), end=float(s.end), text=s.text.strip())
        for s in segments_iter
    ]
    meta = {
        "source": str(input_path),
        "datetime": datetime.now().isoformat(timespec="seconds"),
        "model": model_size,
        "language": language or "auto",
        "device": device,
        "compute_type": compute_type,
        "version": 1,
    }
    return Transcript(meta=meta, segments=segments)

def write_transcript(transcript: Transcript, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
