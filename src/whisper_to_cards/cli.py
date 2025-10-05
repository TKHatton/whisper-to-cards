from typing import Optional
from pathlib import Path
import json
import typer

from . import __version__
from .asr import transcribe_audio, write_transcript
from .segment import segment_transcript, write_sections
from .structure import structure_sections
from .cards import load_structured, write_deck_csv, build_apkg
from .render import load_structured as load_structured_notes, write_html, write_pdf
from .tts import build_section_audio

app = typer.Typer(help="Whisper-to-Cards: lecture → dyslexia-friendly notes + Anki.")


@app.callback(invoke_without_command=True)
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", help="Show version and exit", is_eager=True
    )
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
    transcript: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to outputs/transcript.json"
    ),
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
    input: Path = typer.Argument(
        ..., exists=True, readable=True, help="Audio file (wav/mp3/m4a)"
    ),
    outdir: Path = typer.Option(
        Path("outputs"), "--outdir", "-o", help="Output directory"
    ),
    model: str = typer.Option(
        "small", "--model", "-m", help="faster-whisper model size"
    ),
    language: Optional[str] = typer.Option(
        None, "--language", "-l", help="Force language code (e.g., en)"
    ),
    device: str = typer.Option("auto", "--device", help='"cpu", "cuda", or "auto"'),
    compute_type: str = typer.Option(
        "auto", "--compute-type", help='precision: "int8", "float16", "auto"...'
    ),
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
    sections: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to outputs/sections.json"
    ),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o"),
):
    """Create structured notes schema → outputs/structured.json."""
    payload = structure_sections(sections)
    out_path = outdir / "structured.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    typer.echo(
        f"✅ Wrote {out_path} (sections={len(payload.get('sections', []))}, "
        f"glossary={len(payload.get('glossary', []))})"
    )


@app.command()
def cards(
    structured: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to outputs/structured.json"
    ),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o"),
    deck_name: str = typer.Option("Whisper-to-Cards", "--deck-name"),
    csv_only: bool = typer.Option(
        False, "--csv-only", help="Skip .apkg build, write CSV only"
    ),
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


@app.command()
def render(
    structured: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to outputs/structured.json"
    ),
    outdir: Path = typer.Option(Path("outputs"), "--outdir", "-o"),
    title: str = typer.Option("Easy-Read Notes", "--title"),
    audio_dir: Optional[Path] = typer.Option(
        None, "--audio-dir", help="Directory containing per-section MP3s"
    ),
    embed_fonts: bool = typer.Option(True, "--embed-fonts/--no-embed-fonts"),
    pdf: bool = typer.Option(
        True, "--pdf/--no-pdf", help="Also render PDF with WeasyPrint"
    ),
):
    """Render accessible notes → notes.html (+ notes.pdf unless --no-pdf)."""
    data = load_structured_notes(structured)
    outdir.mkdir(parents=True, exist_ok=True)

    # Build audio lookup (optional)
    audio_lookup = None
    audio_rel = None
    if audio_dir:
        audio_lookup = {}
        for s in data.get("sections", []):
            sid = s.get("id", "")
            cand = audio_dir / f"{sid}.mp3"
            if cand.exists():
                audio_lookup[sid] = cand.name
        audio_rel = (
            str(audio_dir.relative_to(outdir))
            if audio_dir.is_absolute()
            else str(audio_dir)
        )

    html_path = outdir / "notes.html"
    write_html(
        data,
        html_path,
        title=title,
        audio_lookup=audio_lookup,
        audio_dir=audio_rel,
        embed_fonts=embed_fonts,
    )
    typer.echo(f"🖨️  Wrote {html_path}")

    if pdf:
        pdf_path = outdir / "notes.pdf"
        try:
            write_pdf(data, pdf_path, title=title, embed_fonts=embed_fonts)
            typer.echo(f"📄 Wrote {pdf_path}")
        except Exception as e:
            typer.echo(f"⚠️  PDF skipped: {e}")


@app.command()
def tts(
    structured: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to outputs/structured.json"
    ),
    outdir: Path = typer.Option(Path("outputs/audio"), "--outdir", "-o"),
    source: str = typer.Option("tldr", "--source", help='"tldr" or "bullets"'),
    voice: str = typer.Option("en-us", "--voice"),
    rate: int = typer.Option(170, "--rate"),
):
    """Generate one MP3 per section (espeak-ng → wav → mp3)."""
    amap = build_section_audio(
        structured, outdir, source=source, voice=voice, rate=rate
    )
    typer.echo(f"🎧 Wrote audio for {len(amap)} sections in {outdir}")


@app.command()
def bundle(
    outdir: Path = typer.Argument(
        Path("outputs"),
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory containing notes.html (+ pdf/audio/fonts).",
    ),
    zip_path: Path = typer.Option(
        Path("dist/w2c_bundle.zip"), "--out", "-o", help="Where to write the zip."
    ),
    include_pdf: bool = typer.Option(
        True, "--pdf/--no-pdf", help="Include notes.pdf if present"
    ),
):
    """Create an offline ZIP with notes.html (+ optional pdf, audio, fonts)."""
    from .export.zipper import make_zip  # lazy import

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zp = make_zip(outdir, zip_path, include_pdf=include_pdf)
    typer.echo(f"📦 Wrote {zp}")
