from pathlib import Path
import subprocess, json

def run(*args):
    subprocess.run(["poetry","run","w2c",*args], check=True)

def test_structure_to_cards(tmp_path: Path):
    # minimal structured fixture
    s = {
      "meta": {"source": "fixture"},
      "sections":[{"id":"sec_01","title":"Test","tldr":"Summary.","bullets":["Point one."],"terms":[],"cloze":["This is {{c1::cloze}}."]}]
    }
    (tmp_path/"structured.json").write_text(json.dumps(s), encoding="utf-8")
    out = tmp_path/"out"; out.mkdir()
    run("render", str(tmp_path/"structured.json"), "-o", str(out), "--no-pdf")
    run("cards", str(tmp_path/"structured.json"), "-o", str(out), "--no-apkg")
    assert (out/"notes.html").exists()
    assert (out/"deck.csv").exists()
