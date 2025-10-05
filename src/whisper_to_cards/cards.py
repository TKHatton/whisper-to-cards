from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
import csv, json, time, random

import genanki

# ---------- I/O ----------

def load_structured(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def ensure_outdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

# ---------- CSV export (human-readable, easy diff) ----------

def write_deck_csv(structured: Dict[str, Any], out_csv: Path, tag_prefix: str = "w2c") -> Path:
    ensure_outdir(out_csv.parent)
    rows: List[List[str]] = []
    for sec in structured.get("sections", []):
        sec_id = sec.get("id", "sec")
        base_tags = [tag_prefix, f"section:{sec_id}"]

        # Basic cards from bullets
        for b in sec.get("bullets", []):
            front = b
            back = sec.get("title", "")
            tags = " ".join(base_tags + ["type:basic"])
            rows.append(["Basic", front, back, tags])

        # Cloze cards (already in cloze format)
        for c in sec.get("cloze", []):
            front = c
            tags = " ".join(base_tags + ["type:cloze"])
            rows.append(["Cloze", front, "", tags])

        # Optional: glossary (Term → Def) as Basic cards
        for t in sec.get("terms", []):
            term, defin = t.get("term","").strip(), t.get("def","").strip()
            if term:
                tags = " ".join(base_tags + ["type:glossary"])
                rows.append(["Basic", term, defin or sec.get("tldr",""), tags])

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Front", "Back", "Tags"])
        w.writerows(rows)
    return out_csv

# ---------- .apkg export (genanki) ----------

def _basic_model(model_id: int) -> genanki.Model:
    return genanki.Model(
        model_id,
        "W2C Basic",
        fields=[{"name":"Front"}, {"name":"Back"}],
        templates=[{
            "name":"Card 1",
            "qfmt":"{{Front}}",
            "afmt":"{{Front}}<hr id=answer>{{Back}}"
        }],
        css=".card{font-family:Lexend,Arial; font-size:18px; line-height:1.5;} hr{margin:12px 0;}"
    )

def _cloze_model(model_id: int) -> genanki.Model:
    return genanki.Model(
        model_id,
        "W2C Cloze",
        fields=[{"name":"Text"}],
        templates=[{
            "name":"Cloze",
            "qfmt":"{{cloze:Text}}",
            "afmt":"{{cloze:Text}}"
        }],
        model_type=genanki.Model.CLOZE,
        css=".card{font-family:Lexend,Arial; font-size:18px; line-height:1.5;}"
    )

def build_apkg(structured: Dict[str, Any], out_pkg: Path, deck_name: str = "Whisper-to-Cards", seed: int | None = None) -> Path:
    ensure_outdir(out_pkg.parent)
    if seed is None:
        seed = int(time.time()) ^ random.randint(0, 1_000_000)

    deck_id = 10_000_000 + (seed % 9_000_000)
    model_seed = 20_000_000 + (seed % 9_000_000)

    basic_model = _basic_model(model_seed + 1)
    cloze_model = _cloze_model(model_seed + 2)
    deck = genanki.Deck(deck_id, deck_name)
    pkg_media: List[str] = []

    def add_note(model: genanki.Model, fields: List[str], tags: List[str]):
        note = genanki.Note(model=model, fields=fields, tags=tags)
        deck.add_note(note)

    for sec in structured.get("sections", []):
        sec_id = sec.get("id", "sec")
        base_tags = ["w2c", f"section:{sec_id}"]

        # Basic
        for b in sec.get("bullets", []):
            add_note(basic_model, [b, sec.get("title","")], base_tags + ["type:basic"])

        # Cloze (already formatted)
        for c in sec.get("cloze", []):
            add_note(cloze_model, [c], base_tags + ["type:cloze"])

        # Glossary
        for t in sec.get("terms", []):
            term, defin = t.get("term","").strip(), t.get("def","").strip()
            if term:
                add_note(basic_model, [term, defin or sec.get("tldr","")], base_tags + ["type:glossary"])

    genanki.Package(deck, media_files=pkg_media).write_to_file(str(out_pkg))
    return out_pkg
