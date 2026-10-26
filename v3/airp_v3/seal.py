"""Leak-check + seal (hash) step for an adjudicated v3 item file.

Leak check against v2, v1-207, and the training corpus (hashes / protected dir
+ optional corpus JSONL). Collisions are dropped from v3, never from the corpus
(brief §4.4). Then hash the sealed file and write a manifest.

  python3 -m airp_v3.seal --items adjudicated.jsonl --out sealed.jsonl \
      --manifest MANIFEST.sha256 \
      [--protected-dir DIR] [--corpus FILE ...] [--corpus-hashes FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import leakcheck, protected
from .fingerprint import sha256_file
from .loader import load_items


def corpus_index(paths: list[Path], field: str = "content"):
    texts = []
    ids = set()
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            ids.add(r.get("id"))
            t = r.get(field) or r.get("text") or r.get("content") or ""
            if t:
                texts.append(t)
    return leakcheck.build_index(texts), ids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--protected-dir", default=None)
    ap.add_argument("--corpus", action="append", default=[], help="training-corpus JSONL (repeatable)")
    ap.add_argument("--drop-log", default=None, help="JSONL of dropped collisions")
    ap.add_argument("--skip-protected", action="store_true",
                    help="skip v2/v1-207 check (offline dry-run without VPS pins)")
    a = ap.parse_args(argv)

    # Loader asserts composed == stored.
    rows = load_items(a.items)

    colliding_ids: set[str] = set()
    reasons: dict[str, list[str]] = {}

    # Protected (v2 + v1-207)
    if not a.skip_protected:
        try:
            pitems, pins_used = protected.load(a.protected_dir)
            # Index per source file so drop reasons name which pin hit.
            by_src = {}
            for it in pitems:
                by_src.setdefault(it["source"], []).append(it)
            for name, items in by_src.items():
                idx = leakcheck.build_index([it["content"] for it in items])
                pid_set = {it["id"] for it in items}
                for r in rows:
                    if r["id"] in pid_set:
                        colliding_ids.add(r["id"])
                        reasons.setdefault(r["id"], []).append(f"protected-id:{name}")
                    elif leakcheck.collides(r["content"], idx):
                        colliding_ids.add(r["id"])
                        reasons.setdefault(r["id"], []).append(f"protected-text:{name}")
            print(f"protected pins: {pins_used}", file=sys.stderr)
        except protected.ProtectedError as e:
            print(f"protected check unavailable: {e}", file=sys.stderr)
            return 2

    # Training corpus
    if a.corpus:
        idx, cids = corpus_index([Path(p) for p in a.corpus])
        for r in rows:
            if r["id"] in cids:
                colliding_ids.add(r["id"])
                reasons.setdefault(r["id"], []).append("corpus-id")
            elif leakcheck.collides(r["content"], idx):
                colliding_ids.add(r["id"])
                reasons.setdefault(r["id"], []).append("corpus-text")

    kept = [r for r in rows if r["id"] not in colliding_ids]
    dropped = [{"id": r["id"], "reasons": reasons.get(r["id"], [])} for r in rows if r["id"] in colliding_ids]

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps({
        "id": r["id"],
        "content": r["content"],
        "expect_primitives": r["expect_primitives"],
        "expect_classes": r["expect_classes"],
        "provenance": r.get("provenance"),
    }, ensure_ascii=False) for r in kept) + ("\n" if kept else ""), encoding="utf-8")

    digest = sha256_file(out)
    man = Path(a.manifest)
    man.write_text(f"{digest}  {out.name}\n", encoding="utf-8")

    if a.drop_log:
        Path(a.drop_log).write_text(
            "\n".join(json.dumps(d, ensure_ascii=False) for d in dropped) + ("\n" if dropped else ""),
            encoding="utf-8",
        )

    summary = {
        "n_in": len(rows),
        "n_kept": len(kept),
        "n_dropped_leak": len(dropped),
        "dropped_ids": [d["id"] for d in dropped],
        "sealed_sha256": digest,
        "manifest": str(man),
        "out": str(out),
    }
    print(json.dumps(summary, indent=2))
    # Also write summary next to manifest
    man.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
