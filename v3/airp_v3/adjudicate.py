"""Mechanical diff, third-model tie-break, drop-with-reason, agreement rates.

Safety-relevant primitives (brief §4.3): self_harm, sexual_activity,
subject_is_minor, violence_person, conveys_method (stance value).
Disagreement on those -> third pass; if all three differ -> drop with reason.
Non-safety qualifier-only disagreement -> take the guide's reading; log it.

  python3 -m airp_v3.adjudicate --labels labels.jsonl --items items.jsonl \
      --guide LABELING-GUIDE.md --out adjudicated.jsonl \
      --provenance provenance.jsonl --report agreement.json [--mock-tiebreak]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .compose import COMPOSITION_2A_SHA256, OBJECTS, QUALIFIERS, STANCES, compose, load_composition
from .label import ELICITATION_MODELS, call_labeler, mock_label, openrouter_spend_usd
import os

SAFETY_OBJECTS = {"self_harm", "sexual_activity", "violence_person"}
SAFETY_QUALIFIERS = {"subject_is_minor"}
SAFETY_STANCE_VALUES = {"conveys_method"}  # stance disagreement involving this value
AGREEMENT_FLOOR = 0.70

# Non-safety qualifiers: guide-reading fallback when only these differ.
NONSAFETY_QUALIFIERS = set(QUALIFIERS) - SAFETY_QUALIFIERS


def _prim_key(p: dict | None) -> tuple | None:
    if p is None:
        return None
    return (p["stance"], tuple(sorted(p["objects"])), tuple(sorted(p["qualifiers"])))


def safety_relevant_diff(a: dict, b: dict) -> list[str]:
    reasons = []
    if a["stance"] != b["stance"]:
        # any stance disagreement is treated as safety-relevant when either side
        # is conveys_method, or always for stance (brief: "disagree on stance")
        reasons.append(f"stance:{a['stance']}!={b['stance']}")
    ao, bo = set(a["objects"]), set(b["objects"])
    for o in sorted((ao ^ bo) & SAFETY_OBJECTS):
        reasons.append(f"object:{o}")
    for o in sorted((ao ^ bo) - SAFETY_OBJECTS):
        reasons.append(f"object_nonsafety:{o}")
    aq, bq = set(a["qualifiers"]), set(b["qualifiers"])
    for q in sorted((aq ^ bq) & SAFETY_QUALIFIERS):
        reasons.append(f"qualifier:{q}")
    for q in sorted((aq ^ bq) & NONSAFETY_QUALIFIERS):
        reasons.append(f"qualifier_nonsafety:{q}")
    return reasons


def is_safety_disagreement(diffs: list[str]) -> bool:
    return any(
        d.startswith("stance:")
        or d.startswith("object:self_harm")
        or d.startswith("object:sexual_activity")
        or d.startswith("object:violence_person")
        or d.startswith("qualifier:subject_is_minor")
        or d == "object:conveys_method"  # not an object; stance covered above
        for d in diffs
    ) or any(d.startswith("stance:") and "conveys_method" in d for d in diffs)


def guide_reading(a: dict, b: dict) -> dict:
    """For non-safety-only disagreements: prefer mention rule and settled defaults.

    - Prefer is_mention_not_use present when either pass has it and stance is describes.
    - Prefer explicit_register off unless both have it (conservative for encourages path).
    - Union of non-safety objects only if both agree on safety objects/stance.
    """
    stance = a["stance"] if a["stance"] == b["stance"] else a["stance"]
    objects = sorted(set(a["objects"]) & set(b["objects"]))
    # For non-safety object diffs, take intersection (conservative).
    quals_a, quals_b = set(a["qualifiers"]), set(b["qualifiers"])
    shared = quals_a & quals_b
    only_a = quals_a - quals_b
    only_b = quals_b - quals_a
    # Prefer is_mention_not_use if either has it and stance describes.
    if stance == "describes" and (
        "is_mention_not_use" in quals_a or "is_mention_not_use" in quals_b
    ):
        shared.add("is_mention_not_use")
    # Drop contested explicit_register / exceeds_common_knowledge / etc. unless both agree.
    for q in list(only_a | only_b):
        if q in NONSAFETY_QUALIFIERS and q != "is_mention_not_use":
            continue  # leave out contested non-safety quals
    return {"stance": stance, "objects": objects, "qualifiers": sorted(shared)}


def agreement_rates(kept_pairs: list[tuple[dict, dict]]) -> dict:
    """Per-primitive and per-class agreement over pairs that were compared (pre-drop)."""
    # Also accept list of (id, a, b)
    stance_agree = 0
    obj_agree = Counter()
    obj_total = Counter()
    qual_agree = Counter()
    qual_total = Counter()
    class_agree = Counter()
    class_total = Counter()
    n = 0
    comp = load_composition(expect_sha256=COMPOSITION_2A_SHA256)
    for a, b in kept_pairs:
        if a is None or b is None:
            continue
        n += 1
        if a["stance"] == b["stance"]:
            stance_agree += 1
        for o in OBJECTS:
            obj_total[o] += 1
            ina, inb = o in a["objects"], o in b["objects"]
            if ina == inb:
                obj_agree[o] += 1
        for q in QUALIFIERS:
            qual_total[q] += 1
            ina, inb = q in a["qualifiers"], q in b["qualifiers"]
            if ina == inb:
                qual_agree[q] += 1
        ca, cb = set(compose(a, comp)), set(compose(b, comp))
        # per-class: agree on presence/absence for each of 11
        from .compose import load_composition as _lc  # noqa
        classes = [c["class"] for c in comp["classes"]]
        for c in classes:
            class_total[c] += 1
            if (c in ca) == (c in cb):
                class_agree[c] += 1
    def rate(num, den):
        return round(num / den, 4) if den else None
    per_primitive = {"stance": rate(stance_agree, n)}
    for o in OBJECTS:
        per_primitive[o] = rate(obj_agree[o], obj_total[o])
    for q in QUALIFIERS:
        per_primitive[q] = rate(qual_agree[q], qual_total[q])
    per_class = {c: rate(class_agree[c], class_total[c]) for c in class_total}
    below = {k: v for k, v in per_primitive.items() if v is not None and v < AGREEMENT_FLOOR}
    return {
        "n_pairs": n,
        "per_primitive": per_primitive,
        "per_class": per_class,
        "below_70pct": below,
        "agreement_floor": AGREEMENT_FLOOR,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--items", required=True, help="original items (for content + id join)")
    ap.add_argument("--guide", required=True)
    ap.add_argument("--out", required=True, help="adjudicated JSONL with expect_primitives")
    ap.add_argument("--provenance", required=True, help="per-item provenance / drop log")
    ap.add_argument("--report", required=True, help="agreement rates JSON")
    ap.add_argument("--tiebreak-model", default="mistralai/mistral-large-2512")
    ap.add_argument("--tiebreak-host", default=None)
    ap.add_argument("--mock-tiebreak", action="store_true")
    a = ap.parse_args(argv)

    if not a.mock_tiebreak:
        if a.tiebreak_model in ELICITATION_MODELS:
            raise SystemExit(f"tiebreak model {a.tiebreak_model} is in elicitation set")
        if a.tiebreak_model.startswith(("openai/", "~openai/")):
            raise SystemExit("OpenAI forbidden")

    items = {json.loads(l)["id"]: json.loads(l) for l in Path(a.items).read_text().split("\n") if l.strip()}
    labels = [json.loads(l) for l in Path(a.labels).read_text().split("\n") if l.strip()]
    guide = Path(a.guide).read_text(encoding="utf-8")
    comp = load_composition(expect_sha256=COMPOSITION_2A_SHA256)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    use_mock = a.mock_tiebreak or not api_key

    kept_pairs: list[tuple[dict, dict]] = []
    out_rows = []
    prov_rows = []
    n_drop = 0
    n_tie = 0
    n_guide = 0
    n_agree = 0

    for lab in labels:
        iid = lab["id"]
        item = items.get(iid)
        if item is None:
            prov_rows.append({"id": iid, "action": "drop", "reason": "missing item content for id"})
            n_drop += 1
            continue
        passes = lab["passes"]
        if len(passes) < 2:
            prov_rows.append({"id": iid, "action": "drop", "reason": f"fewer than 2 passes ({len(passes)})"})
            n_drop += 1
            continue
        p0, p1 = passes[0]["primitives"], passes[1]["primitives"]
        if p0 is None or p1 is None:
            prov_rows.append({"id": iid, "action": "drop", "reason": "labeler error on one or both passes",
                              "errors": [passes[0].get("meta", {}), passes[1].get("meta", {})]})
            n_drop += 1
            continue
        kept_pairs.append((p0, p1))
        if _prim_key(p0) == _prim_key(p1):
            final = p0
            action = "keep_agree"
            reason = "both passes identical"
            n_agree += 1
            tie = None
        else:
            diffs = safety_relevant_diff(p0, p1)
            if is_safety_disagreement(diffs):
                # third pass
                if use_mock:
                    p2, meta2 = mock_label(item["content"], seed=2)
                    n_tie += 1
                else:
                    p2, meta2 = None, {}
                    last_err = None
                    for attempt in range(3):
                        try:
                            p2, meta2 = call_labeler(a.tiebreak_model, a.tiebreak_host, guide, item["content"], api_key)
                            last_err = None
                            break
                        except Exception as e:
                            last_err = e
                            import time as _t; _t.sleep(1.5 * (attempt + 1))
                    n_tie += 1
                    if last_err is not None and p2 is None:
                        final = None
                        action = "drop"
                        reason = f"tie-break failed after safety disagreement {diffs}: {last_err}"
                        n_drop += 1
                        tie = {"primitives": None, "meta": {"error": str(last_err)}}
                        # fall through to provenance write
                        prov_rows.append({
                            "id": iid, "action": action, "reason": reason,
                            "passes": [{"labeler": p["labeler"], "primitives": p["primitives"]} for p in passes],
                            "tiebreak": tie, "final": final,
                        })
                        continue
                tie = {"primitives": p2, "meta": meta2}
                # majority vote on full key
                keys = [_prim_key(p0), _prim_key(p1), _prim_key(p2)]
                counts = Counter(keys)
                top, topn = counts.most_common(1)[0]
                if topn >= 2:
                    final = None
                    for cand in (p0, p1, p2):
                        if _prim_key(cand) == top:
                            final = cand
                            break
                    action = "keep_tiebreak"
                    reason = f"tie-break majority on safety disagreement {diffs}"
                else:
                    final = None
                    action = "drop"
                    reason = f"all three differ on safety disagreement {diffs}"
                    n_drop += 1
            else:
                final = guide_reading(p0, p1)
                action = "keep_guide_reading"
                reason = f"non-safety disagreement {diffs}; guide reading applied"
                n_guide += 1
                tie = None

        prov_rows.append({
            "id": iid,
            "action": action,
            "reason": reason,
            "passes": [{"labeler": p["labeler"], "primitives": p["primitives"]} for p in passes],
            "tiebreak": tie,
            "final": final,
        })
        if final is not None:
            classes = compose(final, comp)
            out_rows.append({
                "id": iid,
                "content": item["content"],
                "expect_primitives": final,
                "expect_classes": classes,
                "provenance": {
                    **(item.get("provenance") or {}),
                    "adjudication": action,
                    "adjudication_reason": reason,
                    "labelers": [p["labeler"] for p in passes],
                },
            })

    rates = agreement_rates(kept_pairs)
    Path(a.out).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + ("\n" if out_rows else ""), encoding="utf-8")
    Path(a.provenance).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in prov_rows) + ("\n" if prov_rows else ""), encoding="utf-8")
    report = {
        "n_input": len(labels),
        "n_kept": len(out_rows),
        "n_dropped": n_drop,
        "n_agree": n_agree,
        "n_tiebreak": n_tie,
        "n_guide_reading": n_guide,
        "agreement": rates,
        "stop_recommended": bool(rates["below_70pct"]),
        "stop_reason": (
            f"primitive agreement under 70%: {rates['below_70pct']}"
            if rates["below_70pct"] else None
        ),
    }
    Path(a.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_input", "n_kept", "n_dropped", "n_agree", "n_tiebreak", "n_guide_reading", "stop_recommended")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
