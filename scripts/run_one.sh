#!/usr/bin/env bash
set -euo pipefail
FILE="${1:?Usage: scripts/run_one.sh path/to/audio.mp3}"
DECK="${2:-General :: Latest Run}"
MODEL="${3:-small}"
echo "▶ ASR ($MODEL)"; poetry run w2c asr "$FILE" -o outputs -m "$MODEL"
echo "▶ Segment";      poetry run w2c segment   outputs/transcript.json -o outputs --max-chars 1200
echo "▶ Structure";    poetry run w2c structure outputs/sections.json   -o outputs
echo "▶ Render";       poetry run w2c render    outputs/structured.json -o outputs --embed-fonts
echo "▶ Bundle";       poetry run w2c bundle outputs -o dist/lecture_easyread.zip
echo "✓ Done"
