from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json
import html
from importlib.resources import files as pkg_files

try:
    from weasyprint import HTML, CSS

    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


# ---------- I/O ----------


def load_structured(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _copy_embedded_fonts(dest_dir: Path) -> None:
    """Copy packaged fonts into outdir/fonts (supports .ttf/.otf/.woff/.woff2)."""
    try:
        src = pkg_files("whisper_to_cards") / "assets" / "fonts"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for p in src.iterdir():
            if p.suffix.lower() in (".ttf", ".otf", ".woff", ".woff2"):
                (dest_dir / p.name).write_bytes(p.read_bytes())
    except Exception:
        # If assets are not packaged, skip silently.
        pass


# ---------- CSS ----------

ACCESSIBLE_CSS = r"""
:root {
  --font-lexend: 'Lexend', system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
  --font-od: 'OpenDyslexic', 'Lexend', system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
  --font-body: var(--font-lexend);
  --scale: 1;              /* A+/A− text scale */
  --max-line: 70ch;
  --text: #111; --bg: #fff; --muted: #555; --accent: #005fcc; --border: #e5e7eb;
}
@media (prefers-color-scheme: dark) {
  :root { --text:#e8eaed; --bg:#121212; --muted:#a1a1aa; --border:#2a2a2a; --accent:#8ab4f8; }
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  font-family: var(--font-body);
  font-size: calc(18px * var(--scale));
  color: var(--text); background: var(--bg);
  line-height: 1.65; margin: 0; padding: 2rem;
}
main { max-width: var(--max-line); margin: 0 auto; }
header { display:flex; gap:.5rem; align-items:center; justify-content:space-between; margin:0 0 1rem; }
.controls { display:flex; gap:.5rem; flex-wrap:wrap; }
button {
  font: inherit; padding:.45rem .7rem; border-radius:10px; border:1px solid var(--border);
  background: transparent; color: var(--text); cursor:pointer;
}
button:hover { background: rgba(127,127,127,.08); }
small { color: var(--muted); }
h1, h2 { line-height: 1.3; }
h1 { font-size: 1.8rem; margin: 0 0 .25rem; }
h2 { font-size: 1.2rem; margin: 2rem 0 0.5rem; }
ul { padding-left: 1.2rem; } li { margin: 0.3rem 0; }
.tldr { border: 2px solid var(--border); background: rgba(127,127,127,.06); padding: .75rem 1rem; margin: .75rem 0 .25rem; border-radius: 10px; }
.tldr b { color: var(--accent); }
.section { border-top: 1px solid var(--border); padding-top: 1rem; margin-top: 1rem; }
.meta, .footer-note { color: var(--muted); font-size: .9rem; }
.glossary dt { font-weight: 600; }
.glossary dd { margin: 0 0 .75rem 0; }
a { color: var(--accent); text-decoration: underline; }
@page { size: A4; margin: 1in; }

:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
  border-radius: 8px;
}

/* runtime toggles */
.od { --font-body: var(--font-od); }
.dark { --text:#e8eaed; --bg:#121212; --muted:#a1a1aa; --border:#2a2a2a; --accent:#8ab4f8; }

/* WCAG skip link */
.skip-link {
  position:absolute; left:-9999px; top:auto; width:1px; height:1px; overflow:hidden;
}
.skip-link:focus {
  position:static; width:auto; height:auto; padding:.4rem .6rem; border:1px solid var(--border);
  border-radius:10px; background:#fff; color:#000; display:inline-block; margin-bottom:.5rem;
}

:root { --accent: #0b63ff; }               /* light */
.dark { --accent: #93c1ff; }               /* dark */
"""

# Local @font-face rules. Adjust filenames if you used different ones.
FONTS_CSS = r"""
@font-face {
  font-family: 'Lexend';
  src:
    url('fonts/Lexend-VariableFont_wght.woff2') format('woff2'),
    url('fonts/Lexend-VariableFont_wght.ttf') format('truetype');
  font-weight: 100 900; font-style: normal; font-display: swap;
}
/* If you also fetched OpenDyslexic (.otf or .ttf) */
@font-face {
  font-family: 'OpenDyslexic';
  src:
    url('fonts/OpenDyslexic-Regular.woff2') format('woff2'),
    url('fonts/OpenDyslexic-Regular.woff') format('woff'),
    url('fonts/OpenDyslexic-Regular.otf') format('opentype'),
    url('fonts/OpenDyslexic-Regular.ttf') format('truetype');
  font-weight: 400; font-style: normal; font-display: swap;
}
"""


# ---------- HTML ----------


def _escape(s: str) -> str:
    return html.escape(s or "")


def _render_section(
    sec: Dict[str, Any],
    audio_lookup: Dict[str, str] | None = None,
    audio_dir: str | None = None,
) -> str:
    title = _escape(sec.get("title", ""))
    tldr = _escape(sec.get("tldr", ""))
    bullets: List[str] = sec.get("bullets", []) or []
    terms: List[Dict[str, str]] = sec.get("terms", []) or []
    sid = _escape(sec.get("id", ""))

    bullets_html = "".join(f"<li>{_escape(b)}</li>" for b in bullets)

    audio_html = ""
    if audio_lookup and audio_dir:
        fname = audio_lookup.get(sec.get("id", ""))
        if fname:
            audio_src = f"{audio_dir.rstrip('/')}/{fname}"
            audio_html = f"<p><audio controls preload='none' src='{_escape(audio_src)}' aria-label='Audio for {sid}'></audio></p>"

    glossary_html = ""
    if terms:
        gl_items = []
        for t in terms:
            term = _escape(t.get("term", ""))
            defin = _escape(t.get("def", ""))
            if term:
                gl_items.append(f"<dt>{term}</dt><dd>{defin}</dd>")
        glossary_html = f"""
        <h3>Glossary</h3>
        <dl class='glossary'>
          {''.join(gl_items)}
        </dl>
        """

    return f"""
    <section class="section" aria-labelledby="{sid}">
      <h2 id="{sid}">{title}</h2>
      <div class="tldr"><b>TL;DR:</b> {tldr}</div>
      {audio_html}
      {'<h3>Key points</h3>' if bullets else ''}
      {'<ul>' + bullets_html + '</ul>' if bullets else ''}
      {glossary_html}
    </section>
    """


def build_html(
    structured: Dict[str, Any],
    title: str = "Easy-Read Notes",
    audio_lookup: Dict[str, str] | None = None,
    audio_dir: str | None = None,
    embed_fonts: bool = True,
) -> str:
    sections = structured.get("sections", [])
    meta_src = _escape(structured.get("meta", {}).get("source", ""))
    sec_html = "\n".join(_render_section(s, audio_lookup, audio_dir) for s in sections)

    # Web Lexend for online fallback. Local @font-face takes precedence when present.
    web_fonts = "<link href='https://fonts.googleapis.com/css2?family=Lexend:wght@100..900&display=swap' rel='stylesheet'>"

    js = r"""
<script>
(function(){
  const root = document.documentElement;
  const LS = window.localStorage || null;
  const saved = LS ? JSON.parse(LS.getItem('w2c_prefs') || '{}') : {};
  if (saved.font === 'od') root.classList.add('od');
  if (saved.theme === 'dark') root.classList.add('dark');
  if (saved.scale) root.style.setProperty('--scale', saved.scale);

  function save(){
    if(!LS) return;
    const prefs = {
      font: root.classList.contains('od') ? 'od' : 'lexend',
      theme: root.classList.contains('dark') ? 'dark' : 'light',
      scale: getComputedStyle(root).getPropertyValue('--scale').trim() || '1'
    };
    LS.setItem('w2c_prefs', JSON.stringify(prefs));
  }

  function setPressed(btn, on){ if(btn) btn.setAttribute('aria-pressed', on ? 'true' : 'false'); }

  window.toggleFont = function(btn){
    root.classList.toggle('od');
    setPressed(btn, root.classList.contains('od'));
    save();
  }

  window.toggleTheme = function(btn){
    root.classList.toggle('dark');
    setPressed(btn, root.classList.contains('dark'));
    save();
  }

  function setScale(x){ root.style.setProperty('--scale', x.toFixed(2)); save(); }
  window.fontBigger = function(){ const cur=parseFloat(getComputedStyle(root).getPropertyValue('--scale'))||1; setScale(Math.min(cur+0.1, 1.8)); }
  window.fontSmaller = function(){ const cur=parseFloat(getComputedStyle(root).getPropertyValue('--scale'))||1; setScale(Math.max(cur-0.1, 0.8)); }
  window.fontReset  = function(){ setScale(1.0); }

  // Initialize aria-pressed on load
  window.addEventListener('DOMContentLoaded', () => {
    setPressed(document.getElementById('btn-font'),  root.classList.contains('od'));
    setPressed(document.getElementById('btn-dark'),  root.classList.contains('dark'));
  });
})();
</script>
"""

    header = f"""
<header>
  <div>
    <a class="skip-link" href="#main">Skip to content</a>
    <h1>{_escape(title)}</h1>
    <small class="meta">Source: {meta_src}</small>
  </div>
  <div class="controls" role="toolbar" aria-label="Display options">
  <button id="btn-font" type="button" onclick="toggleFont(this)" aria-pressed="false" title="Toggle Lexend / Dyslexic font">Font</button>
  <button id="btn-dark" type="button" onclick="toggleTheme(this)" aria-pressed="false" title="Toggle light / dark">Dark</button>
  <button type="button" onclick="fontSmaller()" aria-label="Decrease text size">A−</button>
  <button type="button" onclick="fontBigger()"  aria-label="Increase text size">A+</button>
  <button type="button" onclick="fontReset()"   aria-label="Reset text size">Reset</button>
</div>
</header>
"""

    fonts_css = FONTS_CSS if embed_fonts else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{_escape(title)}</title>
  {web_fonts}
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>{fonts_css}{ACCESSIBLE_CSS}</style>
</head>
<body>
  <main id="main" role="main" tabindex="-1">
    {header}
    {sec_html}
    <p class="footer-note">Generated by Whisper-to-Cards.</p>
  </main>
  {js}
</body>
</html>
"""


def write_html(
    structured: Dict[str, Any],
    out_html: Path,
    title: str = "Easy-Read Notes",
    audio_lookup: Dict[str, str] | None = None,
    audio_dir: str | None = None,
    embed_fonts: bool = True,
) -> Path:
    ensure_outdir(out_html.parent)
    if embed_fonts:
        _copy_embedded_fonts(out_html.parent / "fonts")
    html_str = build_html(
        structured,
        title=title,
        audio_lookup=audio_lookup,
        audio_dir=audio_dir,
        embed_fonts=embed_fonts,
    )
    out_html.write_text(html_str, encoding="utf-8")
    return out_html


def write_pdf(
    structured: Dict[str, Any],
    out_pdf: Path,
    title: str = "Easy-Read Notes",
    embed_fonts: bool = True,
) -> Path:
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint is not installed or failed to import.")
    ensure_outdir(out_pdf.parent)
    if embed_fonts:
        _copy_embedded_fonts(out_pdf.parent / "fonts")
    # base_url is key so @font-face url('fonts/...') resolves for PDF
    html_str = build_html(structured, title=title, embed_fonts=embed_fonts)
    HTML(string=html_str, base_url=str(out_pdf.parent)).write_pdf(
        str(out_pdf), stylesheets=[CSS(string=FONTS_CSS + ACCESSIBLE_CSS)]
    )
    return out_pdf
