"""Safety-positive supplement (DRAFT, UNSIGNED): subject_is_minor source from benign collected outputs.

Candidate filter = code-level keyword + regex list of generic age and school terms only (guide settled rules 5-6).
Text is scanned in memory and never printed, logged, or written; only ids and counts leave this module.

  python3 -m airp_v3.minor_supplement count --labels-dir DIR --a4 combined-test-a4.jsonl --report report.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from .compose import COMPOSITION_2A_SHA256, compose, load_composition
from .xside import ROOT, SOURCES, TEST_TRIO, classes_of, load_labels, sha

# Generic age terms (whole words, case-insensitive).
AGE_KEYWORDS = ("child", "children", "kid", "kids", "toddler", "toddlers", "infant", "infants", "baby", "babies",
                "teen", "teens", "teenager", "teenagers", "preteen", "pre-teen", "adolescent", "adolescents",
                "minors", "underage", "under-age", "juvenile", "juveniles", "youngster", "youngsters")
# Generic school terms (whole words / phrases, case-insensitive).
SCHOOL_KEYWORDS = ("kindergarten", "preschool", "pre-school", "nursery school", "elementary school", "primary school",
                   "middle school", "junior high", "high school", "secondary school", "grade school", "classroom",
                   "classmate", "classmates", "schoolchild", "schoolchildren", "schoolkid", "schoolkids", "pupil",
                   "pupils", "homework", "recess")
# Numeric ages and grade levels.
REGEXES = (
    r"\b(?:[1-9]|1[0-7])[\s-]*(?:years?|yrs?)[\s-]*old\b",           # "12-year-old", "9 years old"
    r"\baged?\s+(?:[1-9]|1[0-7])\b",                                  # "aged 10", "age 7"
    r"\b(?:[1-9]|1[0-2])(?:st|nd|rd|th)[\s-]*grade(?:rs?)?\b",       # "5th grade", "3rd-grader"
    r"\bgrade\s+(?:[1-9]|1[0-2])\b",                                  # "grade 8"
    r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)[\s-]+grade(?:rs?)?\b",
    r"\ba\s+minor\b(?=\s*(?:[.,;:)!?]|$|\s+(?:who|under|is|was|in|or|and)\b))",  # noun "a minor", not "a minor issue"
    r"\bunder\s+(?:13|16|18|eighteen|thirteen|sixteen)\b",
)
MARKER_PATTERNS = [re.compile(r"\b" + re.escape(k).replace(r"\ ", r"\s+") + r"\b", re.I) for k in AGE_KEYWORDS + SCHOOL_KEYWORDS] \
    + [re.compile(r, re.I) for r in REGEXES]
EXCLUDE_IF_ANY_LABELER = {"objects": {"sexual_activity"}, "classes": {"child_sexual_exploitation", "sexual_content",
                                                                       "self_harm"}}


def has_marker(text: str) -> bool:
    return any(p.search(text) for p in MARKER_PATTERNS)


def count(labels_dir, a4_path, report, train_glm=True) -> dict:
    comp = load_composition(None, COMPOSITION_2A_SHA256)
    labs = {k: load_labels(Path(labels_dir) / f"labels-{k}.jsonl") for k in TEST_TRIO}
    a4 = {}
    for l in Path(a4_path).read_text().splitlines():
        if l.strip():
            r = json.loads(l); a4[r["id"]] = r
    c, cand, dropped, pos = Counter(), [], [], []
    for path, key, cap, h in SOURCES["test"]:
        if sha(path) != h:
            raise SystemExit(f"source sha mismatch {path}")
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line); pv = r["provenance"]
            iid = f"{r['id']}@cap{cap}"
            c[f"rows:{pv['prompt_kind']}"] += 1
            if pv["prompt_kind"] != "benign":
                continue
            if not has_marker(r["content"] or ""):
                continue
            c["benign_marker_hits"] += 1
            L = [labs[k].get(iid) for k in TEST_TRIO]
            if any(p is None for p in L) and all(p is None for p in L):
                c["unlabeled"] += 1; continue
            bad = any(p is not None and (set(p["objects"]) & EXCLUDE_IF_ANY_LABELER["objects"]
                                         or classes_of(p, comp) & EXCLUDE_IF_ANY_LABELER["classes"]) for p in L)
            if bad:
                dropped.append(iid); continue
            cand.append(iid)
            c[f"candidates:{pv['prompt_set']}"] += 1
            c[f"candidates:{key}@cap{cap}"] += 1
            fin = a4.get(iid, {}).get("final_primitives")
            n_sim = sum(p is not None and "subject_is_minor" in p["qualifiers"] for p in L)
            c[f"candidates_labelers_marking_sim:{n_sim}"] += 1
            if fin is not None and "subject_is_minor" in fin["qualifiers"]:
                assert "child_sexual_exploitation" not in compose(fin, comp)
                pos.append(iid)
    uniq = lambda ids: len({i.rsplit("@cap", 1)[0] for i in ids})
    rep = {"filter": {"age_keywords": len(AGE_KEYWORDS), "school_keywords": len(SCHOOL_KEYWORDS), "regexes": len(REGEXES)},
           "scope": "test-side collected outputs, prompt_kind=benign (oasst2-firstturn, xstest benign), 4 writers x 2 caps",
           "counts": dict(sorted(c.items())),
           "dropped_by_label_screen": len(dropped), "dropped_ids": dropped,
           "candidates": len(cand), "candidates_unique_prompt_writer": uniq(cand),
           "stored_label_positives_a4": len(pos), "stored_label_positives_unique_prompt_writer": uniq(pos),
           "positive_ids": pos, "candidate_ids_sha256": __import__("hashlib").sha256("\n".join(cand).encode()).hexdigest()}
    if train_glm:  # information only: train-role outputs are excluded from an eval supplement (train/test overlap)
        p = f"{ROOT}/out800-derived/glm-4.5-air.jsonl"; n = 0
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                n += r["provenance"]["prompt_kind"] == "benign" and has_marker(r["content"] or "")
        rep["excluded_train_role_glm_benign_marker_hits"] = n
    Path(report).write_text(json.dumps(rep, indent=1))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("count")
    for x in ("--labels-dir", "--a4", "--report"): c.add_argument(x, required=True)
    o = ap.parse_args(argv)
    r = count(o.labels_dir, o.a4, o.report)
    print(json.dumps({k: v for k, v in r.items() if not k.endswith("_ids")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
