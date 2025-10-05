from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any
import json, re

@dataclass
class StructuredSection:
    id: str
    title: str
    bullets: List[str]
    tldr: str
    terms: List[Dict[str, str]]
    cloze: List[str]

# add near the top
_STOP_END = (".", "!", "?")

def _clean_bullets(bullets):
    seen = set()
    out = []
    for b in bullets:
        bb = b.strip()
        if not bb:
            continue
        if not bb.endswith(_STOP_END):
            bb += "."
        key = bb.lower()
        if key not in seen:
            seen.add(key)
            out.append(bb)
    return out[:6]  # cap at 6

def _load_sections(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

_sentence_split = re.compile(r"(?<=[.!?])\s+")

def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _sentence_split.split(text) if s.strip()]

def _make_bullets(text: str, max_items: int = 6, max_len: int = 140) -> List[str]:
    """Heuristic bullets: first N meaningful sentences; truncate gently."""
    out = []
    for s in _sentences(text):
        s = re.sub(r"\s+", " ", s)
        if 15 <= len(s) <= max_len:
            out.append(s)
        elif len(s) > max_len:
            out.append(s[: max_len - 1].rstrip() + "…")
        if len(out) >= max_items:
            break
    # prefer leading-verb style (soft heuristic)
    return out

def _make_tldr(text: str, max_len: int = 160) -> str:
    if not text:
        return ""
    first = _sentences(text)[0] if _sentences(text) else text
    s = re.sub(r"\s+", " ", first)
    return s if len(s) <= max_len else (s[: max_len - 1].rstrip() + "…")

_np = re.compile(r"\b([A-Z][a-zA-Z0-9\-]*(?:\s+[A-Z][a-zA-Z0-9\-]*){0,3})\b")

def _extract_terms(text: str, max_items: int = 8) -> List[Dict[str, str]]:
    """Very naive term extractor: capitalized noun-phrases; de-dup; keep short."""
    candidates = []
    seen = set()
    for m in _np.finditer(text):
        term = m.group(1).strip()
        if len(term) < 3 or len(term.split()) > 4:
            continue
        low = term.lower()
        if low not in seen:
            seen.add(low)
            candidates.append(term)
        if len(candidates) >= 30:
            break
    # simple definitions placeholder (will improve later or with LLM)
    terms = [{"term": t, "def": ""} for t in candidates[:max_items]]
    return terms

def _make_cloze(bullets: List[str], max_items: int = 4) -> List[str]:
    """Create cloze deletions by hiding one key word (last significant token)."""
    cloze = []
    for b in bullets:
        words = b.split()
        # pick last significant token
        for i in range(len(words) - 1, -1, -1):
            w = re.sub(r"[^\w\-]", "", words[i])
            if len(w) >= 4:
                words[i] = "{{c1::" + w + "}}"
                cloze.append(" ".join(words))
                break
        if len(cloze) >= max_items:
            break
    return cloze

def structure_sections(sections_json: Path) -> Dict[str, Any]:
    data = _load_sections(sections_json)
    structured: List[StructuredSection] = []
    for sec in data.get("sections", []):
        text = sec.get("text", "")
        title = sec.get("title", "").strip() or "Untitled section"
        bullets = _make_bullets(text)
        tldr = _make_tldr(text)
        bullets = [b for b in bullets if b.strip().lower() != tldr.strip().lower()]
        bullets = _clean_bullets(bullets)
        terms = _extract_terms(text)
        cloze = _make_cloze(bullets)
        structured.append(
            StructuredSection(
                id=sec["id"], title=title, bullets=bullets, tldr=tldr, terms=terms, cloze=cloze
            )
        )
    return {
        "meta": {"source": str(sections_json), "version": 1},
        "sections": [asdict(s) for s in structured],
        "glossary": _merge_glossary(structured),
        "takeaways": _collect_takeaways(structured),
    }

def _merge_glossary(items: List[StructuredSection]) -> List[Dict[str, str]]:
    g: Dict[str, str] = {}
    for s in items:
        for t in s.terms:
            key = t["term"].strip()
            if key and key not in g:
                g[key] = t["def"]
    return [{"term": k, "def": v} for k, v in g.items()]

def _collect_takeaways(items: List[StructuredSection]) -> List[str]:
    # one-line takeaway per section (use TL;DR)
    return [s.tldr for s in items if s.tldr]
