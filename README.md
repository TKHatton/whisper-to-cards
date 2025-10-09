# Whisper-to-Cards

Turn audio (talks, lectures, tutorials) into **accessible notes** + **tagged, actionable flashcards** (Anki).
Works in **GitHub Codespaces** and publishes a public /**demo**/ page via GitHub Pages.

**Live demo:** https://tkhatton.github.io/whisper-to-cards/  
**Repo:** https://github.com/TKHatton/whisper-to-cards


## Quick Start (TL;DR)

1. Put audio in inputs/ (mp3/m4a/wav).
2. Process one file:
```
scripts/run_one.sh "inputs/YourFile.mp3" "Odin :: Foundations" small
```

3. Make a deck (pick one):

```
poetry run python scripts/make_decks.py --mode ds
# or
poetry run python scripts/make_decks.py --mode git
```

4. (Optional) Publish demo:

```
scripts/publish.sh
```

## One-Time Setup

These are already added in this repo. If anything’s missing, re-create from the chat.
```
chmod +x scripts/run_one.sh
chmod +x scripts/make_decks.py
# (optional) if you have publish.sh and auto_run.py:
chmod +x scripts/publish.sh
```

For .apkg export (optional):
poetry add genanki

## What the scripts do

`scripts/run_one.sh <audio> "<Deck Name>" <model>`

Runs ASR → segment → structure → render → bundle.

* `model`: `small` (fast, default) or `medium` (more accurate).

`scripts/make_decks.py --mode ds|git`

Builds **tagged Anki decks** from your run:

* `--mode ds`: Data Structures (definitions, when-to-use, safe Big-O).

* `--mode git`: Git/VS Code (how-to, commands, concepts).
    
* Outputs: `outputs/*.csv` and (if `genanki` installed) `outputs/*.apkg`.

* `scripts/publish.sh` (optional)
Copies your featured deck to `outputs/deck.apkg`, bundles `outputs/`, and pushes so `/demo/` updates.

## Automatic Mode (Drop-a-file → Runs)

Leave this watcher running in one terminal tab:

```
poetry run python scripts/auto_run.py
```

Now **whenever you add/modify** an audio file in `inputs/`, it will:

* run `run_one.sh` on that file,

* generate a DS deck by default (change to `git` inside `auto_run.py`),

* (optionally) publish (uncomment the line inside `auto_run.py`).

    The watcher stays idle when no new files appear. Stop with **Ctrl+C**.


## Demo Site (GitHub Pages)

    Local/Codespaces: open the forwarded port URL → `/demo/`.

    Public: `https://tkhatton.github.io/whisper-to-cards/demo/`

    The demo iframe reads `outputs/notes.html`; buttons download PDF/CSV/APKG/ZIP.

## Troubleshooting

* Script says “Usage: … path/to/audio.mp3” → you didn’t pass a real file path.

* Nothing happens in watcher → add/modify a file in `inputs/`.

* 404 in demo iframe → ensure `outputs/notes.html` is committed & Pages is deployed.

* Windows line endings → `sed -i 's/\r$//' scripts/*.sh`

* Force add generated files (ignored by `.gitignore`):
    `git add -f outputs/ dist/`
---
