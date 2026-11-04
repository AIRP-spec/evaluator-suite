"""In-set collision check (declared v3 rule, Justin t214u 2026-11-02).

Rows inside ONE set must not collide with each other under the same leak rules used
against training and the held-out suites (airp_v3.leakcheck / leak.mjs): exact match
after normalisation; substring when both sides are >= 40 chars; word 4-gram Jaccard
>= 0.5. Thresholds are the declared ones and are not tuned per run.

Resolution rule (deterministic, handles chains): sort rows by id ascending (Python
str order, i.e. code-point order); walk in that order; a row is DROPPED if it
collides with any row already KEPT, otherwise it is kept. A dropped row never
causes another drop, so for A<B<C with A~B and B~C but not A~C, A and C are kept and
B is dropped. Each drop records the kept id it collided with (lowest such id).
Rows listed in `protect` are never dropped; if a protected row would be dropped the
result reports it under `protected_conflicts` (the caller must stop).

Prints ids and counts only; never prints text.

  python3 -m airp_v3.inset --items FILE.jsonl [--field content]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import leakcheck

RULE = "in-set: exact | substring>=40 (both sides) | word 4-gram jaccard>=0.50; ids ascending, drop row colliding with an earlier KEPT row"


def resolve(rows, field: str | None = None, jaccard_limit: float = 0.5, protect=()):
    """rows: iterable of dicts with 'id' and a text field. Returns dict (ids/counts only)."""
    protect = set(protect)
    items = []
    for r in rows:
        f = field or next((k for k in leakcheck.TEXT_FIELDS if isinstance(r.get(k), str)), None)
        if f is None:
            raise ValueError(f"row id={r.get('id')} has no text field")
        items.append((str(r["id"]), r[f]))
    ids = [i for i, _ in items]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate ids")
    items.sort(key=lambda x: x[0])
    kept: list[tuple[str, dict]] = []  # (id, single-entry index)
    dropped: dict[str, str] = {}
    conflicts: dict[str, str] = {}
    for rid, text in items:
        hit = None
        for kid, kidx in kept:
            if leakcheck.collides(text, kidx, jaccard_limit) or (
                    (leakcheck.normalize(text) and leakcheck.collides(kidx["_text"], leakcheck.build_index([text]), jaccard_limit))):
                hit = kid
                break
        if hit is not None and rid in protect:
            conflicts[rid] = hit
            hit = None
        if hit is None:
            idx = leakcheck.build_index([text])
            idx["_text"] = text
            kept.append((rid, idx))
        else:
            dropped[rid] = hit
    return {"rule": RULE, "n_in": len(items), "n_kept": len(kept), "n_dropped": len(dropped),
            "kept_ids": [k for k, _ in kept], "dropped": dropped, "protected_conflicts": conflicts}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", required=True)
    ap.add_argument("--field")
    a = ap.parse_args(argv)
    rows = [json.loads(l) for l in Path(a.items).read_text("utf-8").split("\n") if l.strip()]
    res = resolve(rows, a.field)
    res.pop("kept_ids")
    print(json.dumps(res, indent=1))
    return 1 if res["n_dropped"] else 0


if __name__ == "__main__":
    sys.exit(main())
