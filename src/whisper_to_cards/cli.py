from typing import Optional
from pathlib import Path
import json
import typer

from . import __version__
from .asr import transcribe_audio, write_transcript
from .segment import segment_transcript, write_sections
from .structure import structure_sections
from .cards import load_structured, write_deck_csv, build_apkg

app = typer.Typer(help="Whisper-to-Cards: lecture → dyslexia-friendly notes + Anki.")

@app.callback(invoke_without_command=True)
def main(
    version: Optional[bool] = typer.Option(None, "--version", help="Show version and exit", is_eager=True)
):
    if version:
        typer.echo(f"whisper-to-cards {__version__}")
        raise typer.Exit()

@app.command()
def hello(name: str = "Lenise"):
    """Sanity-check command."""
    typer.echo(f"👋 Hello, {name}! Your CLI is alive.")

@app.command()
def version():
    """Show version."""
    typer.echo(f"whisper-to-cards {__version__}")

@app.command()
def segment(
    transcript: Path = typer.Argument(..., exists=True, readable=True, help="Path to outputs/transcript.json"),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o"),
    max_chars: int = typer.Option(1200, help="Target characters per section"),
):
    """Group raw ASR segments into topic-sized sections → outputs/sections.json."""
    secs = segment_transcript(transcript_path=transcript, max_chars=max_chars)
    meta = {"source": str(transcript), "max_chars": max_chars, "version": 1}
    out_path = outdir / "sections.json"
    write_sections(secs, out_path, meta=meta)
    typer.echo(f"✅ Wrote {out_path} with {len(secs)} sections")

@app.command()
def asr(
    input: Path = typer.Argument(..., exists=True, readable=True, help="Audio file (wav/mp3/m4a)"),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o", help="Output directory"),
    model: str = typer.Option("small", "--model", "-m", help="faster-whisper model size"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Force language code (e.g., en)"),
    device: str = typer.Option("auto", "--device", help='"cpu", "cuda", or "auto"'),
    compute_type: str = typer.Option("auto", "--compute-type", help='precision: "int8", "float16", "auto"...'),
):
    """Transcribe audio → outputs/transcript.json (timestamps + text)."""
    typer.echo("🎧 Transcribing...")
    transcript = transcribe_audio(
        input_path=input,
        model_size=model,
        language=language,
        device=device,
        compute_type=compute_type,
    )
    out_path = outdir / "transcript.json"
    write_transcript(transcript, out_path)
    typer.echo(f"✅ Wrote {out_path}")

@app.command()
def structure(
    sections: Path = typer.Argument(..., exists=True, readable=True, help="Path to outputs/sections.json"),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o"),
):
    """Create structured notes schema → outputs/structured.json."""
    payload = structure_sections(sections)
    out_path = outdir / "structured.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(
        f"✅ Wrote {out_path} (sections={len(payload.get('sections', []))}, "
        f"glossary={len(payload.get('glossary', []))})"
    )

@app.command()
def cards(
    structured: Path = typer.Argument(..., exists=True, readable=True, help="Path to outputs/structured.json"),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o"),
    deck_name: str = typer.Option("Whisper-to-Cards", "--deck-name"),
    csv_only: bool = typer.Option(False, "--csv-only", help="Skip .apkg build, write CSV only"),
):
    """Create Anki deck files → deck.csv (+ deck.apkg unless --csv-only)."""
    data = load_structured(structured)
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "deck.csv"
    write_deck_csv(data, csv_path)
    typer.echo(f"📝 Wrote {csv_path}")

    if not csv_only:
        pkg_path = outdir / "deck.apkg"
        build_apkg(data, pkg_path, deck_name=deck_name)
        typer.echo(f"📦 Wrote {pkg_path}")
