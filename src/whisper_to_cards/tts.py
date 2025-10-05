from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json
import subprocess
from pydub import AudioSegment  # needs ffmpeg on PATH


def load_structured(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _espeak_wav(
    text: str, out_wav: Path, voice: str = "en-us", rate: int = 170
) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    # espeak-ng writes WAV directly
    cmd = ["espeak-ng", "-v", voice, "-s", str(rate), "-w", str(out_wav), text]
    subprocess.run(cmd, check=True)


def _wav_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "128k") -> None:
    audio = AudioSegment.from_wav(wav_path)
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(mp3_path), format="mp3", bitrate=bitrate)


def build_section_audio(
    structured_json: Path,
    outdir: Path,
    source: str = "tldr",  # "tldr" or "bullets"
    voice: str = "en-us",
    rate: int = 170,
) -> Dict[str, str]:
    """
    Returns a map {section_id: relative mp3 path} for sections that produced audio.
    """
    data = load_structured(structured_json)
    outdir.mkdir(parents=True, exist_ok=True)
    audio_map: Dict[str, str] = {}

    for sec in data.get("sections", []):
        sid = sec.get("id", "sec")
        if source == "bullets":
            # join first 3 bullets, keep short
            bullets = sec.get("bullets", [])[:3]
            text = ". ".join(bullets)
        else:
            text = sec.get("tldr", "") or (sec.get("title", "") or "")
        text = (text or "").strip()
        if not text:
            continue

        wav_path = outdir / f"{sid}.wav"
        mp3_path = outdir / f"{sid}.mp3"
        _espeak_wav(text, wav_path, voice=voice, rate=rate)
        _wav_to_mp3(wav_path, mp3_path)
        try:
            wav_path.unlink()
        except Exception:
            pass
        audio_map[sid] = mp3_path.name  # store basename; HTML will use audio_dir + name

    # also save a small sidecar for debugging
    (outdir / "audio_map.json").write_text(
        json.dumps(audio_map, indent=2), encoding="utf-8"
    )
    return audio_map
