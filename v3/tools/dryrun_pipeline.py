#!/usr/bin/env python3
"""Dry-run the Phase 1 pipeline on the 40 draft items (no OpenRouter collection).

Steps: CSE filter fixture -> (collection skipped/blocked) -> two-pass label ->
adjudicate -> loader assert -> seal (v2/v1-207 + training corpus).

Usage (from v3/):
  python3 tools/dryrun_pipeline.py [--mock] [--protected-dir DIR] [--corpus FILE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRY = ROOT / "dryrun"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=str(ROOT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="offline labelers (no OpenRouter spend)")
    ap.add_argument("--protected-dir", default="/tmp/airp-protected")
    ap.add_argument("--corpus", action="append", default=[])
    a = ap.parse_args(argv)

    out = DRY / "out"
    out.mkdir(parents=True, exist_ok=True)

    # 1. CSE filter on fixture prompts
    run([
        sys.executable, "-m", "airp_v3.filter_cse",
        "--in", str(DRY / "filter-fixture-prompts.jsonl"),
        "--out", str(out / "prompts-kept.jsonl"),
        "--report", str(out / "filter-report.json"),
    ])

    # 2. Collection must refuse without OPENROUTER_APPROVAL
    blocked = out / "collect-blocked.txt"
    rc = subprocess.call([
        sys.executable, "-m", "airp_v3.collect",
        "--prompts", str(out / "prompts-kept.jsonl"),
        "--models", str(DRY / "labelers.json"),
        "--prompt-set", "dryrun-fixture",
        "--out", str(out / "collected.jsonl"),
        "--approval-file", str(ROOT.parent / "OPENROUTER_APPROVAL"),
        "--limit", "1",
    ], cwd=str(ROOT), stdout=blocked.open("w"), stderr=subprocess.STDOUT)
    blocked.write_text(blocked.read_text() + f"\nexit_code={rc}\n")
    if rc == 2:
        print("collect correctly blocked without OPENROUTER_APPROVAL")
    else:
        print(f"WARNING: collect rc={rc}, expected 2", file=sys.stderr)

    # 3. Label the 40 items
    label_cmd = [
        sys.executable, "-m", "airp_v3.label",
        "--items", str(DRY / "items-40.jsonl"),
        "--guide", str(ROOT / "LABELING-GUIDE.md"),
        "--labelers", str(DRY / "labelers.json"),
        "--out", str(out / "labels.jsonl"),
    ]
    if a.mock:
        label_cmd.append("--mock")
    run(label_cmd)

    # 4. Adjudicate
    adj = [
        sys.executable, "-m", "airp_v3.adjudicate",
        "--labels", str(out / "labels.jsonl"),
        "--items", str(DRY / "items-40.jsonl"),
        "--guide", str(ROOT / "LABELING-GUIDE.md"),
        "--out", str(out / "adjudicated.jsonl"),
        "--provenance", str(out / "provenance.jsonl"),
        "--report", str(out / "agreement.json"),
        "--tiebreak-model", "z-ai/glm-4.7-flash",
    ]
    if a.mock:
        adj.append("--mock-tiebreak")
    run(adj)

    # 5. Seal
    seal = [
        sys.executable, "-m", "airp_v3.seal",
        "--items", str(out / "adjudicated.jsonl"),
        "--out", str(out / "sealed.jsonl"),
        "--manifest", str(out / "MANIFEST.sha256"),
        "--drop-log", str(out / "seal-drops.jsonl"),
        "--protected-dir", a.protected_dir,
    ]
    for c in a.corpus:
        seal.extend(["--corpus", c])
    run(seal)

    # 6. Summarize (no safety-class item text)
    agreement = json.loads((out / "agreement.json").read_text())
    filt = json.loads((out / "filter-report.json").read_text())
    seal_summary = json.loads((out / "MANIFEST.summary.json").read_text())
    summary = {
        "filter": {k: filt[k] for k in ("n_in", "n_kept", "n_dropped_category", "n_dropped_keyword")},
        "collect_blocked": rc == 2,
        "adjudication": {k: agreement[k] for k in (
            "n_input", "n_kept", "n_dropped", "n_agree", "n_tiebreak", "n_guide_reading",
            "stop_recommended", "stop_reason",
        )},
        "agreement_per_primitive": agreement["agreement"]["per_primitive"],
        "agreement_per_class": agreement["agreement"]["per_class"],
        "below_70pct": agreement["agreement"]["below_70pct"],
        "seal": seal_summary,
    }
    (out / "DRYRUN-SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
