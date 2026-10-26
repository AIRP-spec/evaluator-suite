"""CSE-category and keyword prompt filter.

Drops CSE-category prompts by category label and by a minor-marker keyword pass,
per standing brief §4.2 / docs/RED-TEAM-PROMPT-SETS.md. Records counts and dropped
ids. Never prints dropped prompt text.

  python3 -m airp_v3.filter_cse --in prompts.jsonl --out kept.jsonl --report report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Category / hazard / harm_area / violated_categories / types_of_harm / SemanticCategory
# values that mean CSE or inseparable child-abuse / adult-sexual-with-no-minor-sublabel
# per docs/RED-TEAM-PROMPT-SETS.md. Matching is case-insensitive substring on the
# joined label fields.
CATEGORY_DROP_SUBSTRINGS = (
    "cse",
    "child sexual",
    "sexual (minor)",
    "sexual minor",
    "sexual/minor",
    "child abuse",  # SimpleSafetyTests mixes sexual and non-sexual; drop whole area
    "child_exploitation",
    "child-exploitation",
    "csam",
    " pedophil",
)

# Label-field names we inspect across the shortlisted sets.
LABEL_FIELDS = (
    "hazard",
    "harm_area",
    "category",
    "Category",
    "SemanticCategory",
    "types_of_harm",
    "violated_categories",
    "label",
    "labels",
    "note",
    "type",
)

# Minor-marker keyword screen from PRIMITIVES.md / settled rules 5–6.
# Applied to remaining prompts after category drop. Hits are dropped by id
# without a human reading them.
MINOR_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\b(?:1[0-7]|[1-9])\s*(?:year|yr|y/o|years?)\s*old\b",
        r"\b(?:age[d]?|turns?)\s*(?:1[0-7]|[1-9])\b",
        r"\b(?:eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen)\s*(?:year|yr)?\b",
        r"\b(?:child|children|kid|kids|toddler|infant|baby|babies)\b",
        r"\b(?:teen|teens|teenager|teenagers|preteen|pre-teen)\b",
        r"\b(?:minor|minors|underage|under-age|under\s*age)\b",
        r"\b(?:boy|girl)s?\b(?=.*\b(?:young|little|small)\b)|\b(?:young|little|small)\s+(?:boy|girl)s?\b",
        r"\b(?:elementary|middle\s*school|high\s*school|grade\s*(?:[1-9]|1[0-2])|classroom|kindergarten|preschool)\b",
        r"\b(?:sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)\s+grader?\b",
        r"\b(?:roleplay|role-play|rp)\b.*\b(?:as\s+a\s+)?(?:child|kid|teen|minor|under\s*18)\b",
        r"\bunder\s*18\b|\bunder\s*eighteen\b|\bu18\b",
    )
]

TEXT_FIELDS = ("prompt", "question", "behavior", "text", "content", "query", "input")


def _labels_of(row: dict) -> list[str]:
    out: list[str] = []
    for f in LABEL_FIELDS:
        if f not in row:
            continue
        v = row[f]
        if v is None:
            continue
        if isinstance(v, list):
            out.extend(str(x) for x in v)
        else:
            out.append(str(v))
    return out


def category_hit(row: dict) -> str | None:
    labels = " | ".join(_labels_of(row)).lower()
    for s in CATEGORY_DROP_SUBSTRINGS:
        if s in labels:
            return s
    return None


def text_of(row: dict) -> str:
    for f in TEXT_FIELDS:
        v = row.get(f)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def keyword_hit(text: str) -> str | None:
    for pat in MINOR_PATTERNS:
        m = pat.search(text)
        if m:
            return pat.pattern
    return None


def filter_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    kept: list[dict] = []
    dropped_category: list[dict] = []
    dropped_keyword: list[dict] = []
    for row in rows:
        rid = row.get("id") or row.get("prompt_id") or row.get("qid")
        hit = category_hit(row)
        if hit is not None:
            dropped_category.append({"id": rid, "reason": f"category:{hit}"})
            continue
        text = text_of(row)
        kh = keyword_hit(text) if text else None
        if kh is not None:
            dropped_keyword.append({"id": rid, "reason": f"keyword:{kh}"})
            continue
        kept.append(row)
    report = {
        "n_in": len(rows),
        "n_kept": len(kept),
        "n_dropped_category": len(dropped_category),
        "n_dropped_keyword": len(dropped_keyword),
        "n_dropped_total": len(dropped_category) + len(dropped_keyword),
        "dropped_category_ids": [d["id"] for d in dropped_category],
        "dropped_keyword_ids": [d["id"] for d in dropped_keyword],
        "dropped": dropped_category + dropped_keyword,
        "category_substrings": list(CATEGORY_DROP_SUBSTRINGS),
        "keyword_pattern_count": len(MINOR_PATTERNS),
    }
    return kept, report


def load_rows(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        for k in ("items", "prompts", "data", "rows"):
            if isinstance(data.get(k), list):
                return data[k]
        raise SystemExit(f"unrecognised JSON shape in {path}")
    rows = []
    for line in raw.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True, help="prompts JSONL or JSON")
    ap.add_argument("--out", required=True, help="kept prompts JSONL")
    ap.add_argument("--report", required=True, help="filter counts JSON (no prompt text)")
    a = ap.parse_args(argv)
    rows = load_rows(Path(a.inp))
    kept, report = filter_rows(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in kept) + ("\n" if kept else ""), encoding="utf-8")
    Path(a.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_in", "n_kept", "n_dropped_category", "n_dropped_keyword", "n_dropped_total")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
