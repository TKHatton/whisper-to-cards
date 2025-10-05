# Whisper-to-Cards
Lecture → dyslexia-friendly notes + Anki, as an OSS pipeline.

## Requirements
- Python 3.12+
- Poetry 2.x
- FFmpeg (for audio decoding)

## Install
```bash
poetry install
# If you’re in a fresh env, also ensure the package is editable:
poetry run pip install -e .
```

## Run the pipeline
```bash
poetry install
poetry run w2c asr examples/lecture.mp3 -o outputs -m small
poetry run w2c segment outputs/transcript.json -o outputs --max-chars 1200
poetry run w2c structure outputs/sections.json -o outputs
poetry run w2c cards outputs/structured.json -o outputs --deck-name "My Lecture Deck"
```

## Quick start (end-to-end)

```bash

# 1) Transcribe audio → outputs/transcript.json
poetry run w2c asr examples/lecture.mp3 -o outputs -m small

# 2) Segment transcript → outputs/sections.json
poetry run w2c segment outputs/transcript.json -o outputs --max-chars 1200

# 3) Structure sections → outputs/structured.json
poetry run w2c structure outputs/sections.json -o outputs

# 4) Make Anki deck → outputs/deck.csv (+ deck.apkg)
poetry run w2c cards outputs/structured.json -o outputs --deck-name "My Lecture Deck"
```

## Output files
outputs/transcript.json – raw ASR segments with timestamps

outputs/sections.json – merged, topic-sized sections

outputs/structured.json – bullets, TL;DR, glossary, cloze

outputs/deck.csv, outputs/deck.apkg – import into Anki

## Tips

Better accuracy: use a bigger model: -m medium (slower).

Force language if you know it: --language en.

If you change source code, reinstall editable: poetry run pip install -e .
---

## `.gitignore` reminder
Make sure your `.gitignore` (at repo root) ignores artifacts:
---

## Commit & push (safe sequence)
```bash
git add -A
git commit -m "docs: README + gitignore; pipeline stable (ASR→segment→structure→Anki)"
git push origin main
```

### Export Anki
```bash
# CSV only
w2c cards outputs/structured.json -o outputs --deck "My Lecture" --no-apkg

# CSV + APKG (requires `genanki`)
w2c cards outputs/structured.json -o outputs --deck "My Lecture" --apkg
```

## outputs: 
outputs/deck.csv, outputs/deck.apkg
```bash

4) **Sanity smoke test (optional)**
```bash
poetry run python - <<'PY'
from pathlib import Path
import json
d=json.load(open("outputs/structured.json"))
assert d["sections"], "no sections found"
print("sections:", len(d["sections"]))
print("exists deck.csv:", Path("outputs/deck.csv").exists())
print("exists deck.apkg:", Path("outputs/deck.apkg").exists())
PY
```
