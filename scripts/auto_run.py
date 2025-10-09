import time, subprocess, sys, os, re
from pathlib import Path

INPUTS = Path("inputs")
INPUTS.mkdir(exist_ok=True)
SEEN = {}

AUDIO = re.compile(r".+\.(mp3|m4a|wav|flac|aac|ogg)$", re.I)

def run(cmd):
  print("▶", " ".join(cmd))
  subprocess.run(cmd, check=True)

def process(path):
  # 1) Notes
  run(["scripts/run_one.sh", str(path), "Odin :: Foundations", "small"])
  # 2) Deck (pick your default: ds or git)
  run(["poetry", "run", "python", "scripts/make_decks.py", "--mode", "ds"])
  # 3) (Optional) publish to website — enable if you want:
  # run(["scripts/publish.sh"])

print("Watching", INPUTS.resolve(), "for new/updated audio… (Ctrl+C to stop)")
while True:
  try:
    for p in INPUTS.iterdir():
      if not AUDIO.match(p.name): 
        continue
      mtime = p.stat().st_mtime
      if SEEN.get(p) != mtime:
        # debounce: wait a bit to ensure copy finished
        SEEN[p] = mtime
        time.sleep(1.0)
        process(p)
    time.sleep(1.0)
  except KeyboardInterrupt:
    sys.exit(0)
  except Exception as e:
    print("WARN:", e)
    time.sleep(2)
