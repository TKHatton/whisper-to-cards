from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
import csv
import json

try:
    import genanki  # optional

    GENANKI = True
except Exception:
    GENANKI = False


# ---------- I/O ----------


def load_structured(path: Path) -> Dict[str, Any]:
    """Read the structured.json produced earlier in the pipeline."""
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- Transform ----------


def _rows_from_structured(data: Dict[str, Any]) -> Tuple[List[List[str]], List[str]]:
    """
    Build rows for a single 'deck.csv' (Basic cards) and a list of Cloze strings.
    - Basic: TL;DR + each bullet become cards.
    - Cloze: each cloze string ({{c1::...}}) will be used for APKG cloze notes.
    """
    basic_rows: List[List[str]] = []
    cloze_texts: List[str] = []

    for sec in data.get("sections", []):
        title = (sec.get("title") or "").strip()
        tldr = (sec.get("tldr") or "").strip()
        bullets: List[str] = sec.get("bullets", []) or []
        clozes: List[str] = sec.get("cloze", []) or []

        if title and tldr:
            basic_rows.append([f"{title} — TL;DR", tldr])

        for i, b in enumerate(bullets, 1):
            b = (b or "").strip()
            if b:
                basic_rows.append([f"{title} — Key point {i}", b])

        for c in clozes:
            c = (c or "").strip()
            if c:
                cloze_texts.append(c)

    return basic_rows, cloze_texts


# ---------- CSV ----------


def write_deck_csv(data: Dict[str, Any], out_csv: Path) -> Path:
    """
    Write a single CSV with Basic cards. Columns: Front, Back.
    (Cloze are used only for APKG — not written here.)
    """
    rows, _cloze = _rows_from_structured(data)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Front", "Back"])
        w.writerows(rows)
    return out_csv


# ---------- APKG (optional) ----------


def build_apkg(
    data: Dict[str, Any], out_apkg: Path, deck_name: str = "Whisper-to-Cards"
) -> Path:
    """
    Create an Anki .apkg with Basic + Cloze if genanki is available.
    - Basic model: Front/Back from deck.csv logic.
    - Cloze model: each cloze string becomes a cloze note.
    """
    if not GENANKI:
        raise RuntimeError(
            "genanki is not installed; run `poetry add genanki` to enable APKG export."
        )

    deck_id = abs(hash(deck_name)) % (10**10)
    deck = genanki.Deck(deck_id, deck_name)

    basic_model = genanki.Model(
        1607392319,  # stable-ish id
        "W2C Basic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": "{{Front}}<hr id=answer>{{Back}}",
            }
        ],
    )

    cloze_model = genanki.Model(
        998877661,
        "W2C Cloze",
        fields=[{"name": "Text"}],
        templates=[
            {"name": "Cloze", "qfmt": "{{cloze:Text}}", "afmt": "{{cloze:Text}}"}
        ],
        model_type=genanki.Model.CLOZE,
    )

    basic_rows, cloze_texts = _rows_from_structured(data)
    for fr, ba in basic_rows:
        deck.add_note(genanki.Note(model=basic_model, fields=[fr, ba]))
    for txt in cloze_texts:
        deck.add_note(genanki.Note(model=cloze_model, fields=[txt]))

    pkg = genanki.Package(deck)
    out_apkg.parent.mkdir(parents=True, exist_ok=True)
    pkg.write_to_file(str(out_apkg))
    return out_apkg
