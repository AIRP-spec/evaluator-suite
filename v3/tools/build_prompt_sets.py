"""Build the v3 (test) and corpus-expansion (train) prompt files from pinned sources.

Self-hosted collection amendment, 2026-11-01. Every source is fetched at a pinned
commit into MEMORY only (never written to disk unfiltered), its sha256 recorded,
reduced to the published prompt text with no wording change, CSE-filtered with
airp_v3.filter_cse.filter_rows (label pass + keyword pass), deduplicated, test rows
colliding with any train prompt dropped (from test, never from train), then each
side shuffled with a fixed seed and assigned round-robin to that side's models.

Writes, per side:  prompts-<side>.jsonl  and  filter-report-<side>.json
The report carries the kept file's sha256 (`out_sha256`); airp_v3.collect refuses
a prompts file whose sha256 differs. Reports hold counts and ids only, never text.

  python3 tools/build_prompt_sets.py --out-dir /root/primitives-evaluator/v3-collect-20261101/prompts
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import random
import sys
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from airp_v3.filter_cse import filter_rows  # noqa: E402
from airp_v3.leakcheck import normalize, word_ngrams  # noqa: E402
from airp_v3.policy import PROMPT_SET_SIDE  # noqa: E402

SEED = 20261101
GH = "https://raw.githubusercontent.com"
HF = "https://huggingface.co/datasets"

SOURCES = {
    "ailuminate-demo": f"{GH}/mlcommons/ailuminate/769cc2be9d20c8d4fb26ce53b68865ed41dfb8e2/airr_official_1.0_demo_en_us_prompt_set_release.csv",
    "simplesafetytests": f"{HF}/Bertievidgen/SimpleSafetyTests/resolve/98223c5d8c4059c8f4d8fe2fec8720ee8a20d3c5/sst_test_cases.csv",
    "xstest": f"{HF}/Paul/XSTest/resolve/f600c994b256f12867dfa5b3eb3d545a3e62f8b5/xstest_prompts.csv",
    "oasst2-firstturn": f"{HF}/OpenAssistant/oasst2/resolve/179dd21fc55192153d94adb0e0ce8f69e222bf75/2023-11-05_oasst2_ready.messages.jsonl.gz",
    "aegis2-train": f"{HF}/nvidia/Aegis-AI-Content-Safety-Dataset-2.0/resolve/d86bb8bedff51d25ac834ab7838f1cc61acb7a2c/train.json",
    "donotanswer": f"{HF}/LibrAI/do-not-answer/resolve/74e74f2e4507ef256fe536f78a776f4a1ff67955/data_en.csv",
    "harmbench-text": f"{GH}/centerforaisafety/HarmBench/8e1604d1171fe8a48d8febecd22f600e462bdcdd/data/behavior_datasets/harmbench_behaviors_text_all.csv",
    "jbb-harmful": f"{HF}/JailbreakBench/JBB-Behaviors/resolve/886acc352a31533ffbcf4ef22c744658688086fc/data/harmful-behaviors.csv",
    "jbb-benign": f"{HF}/JailbreakBench/JBB-Behaviors/resolve/886acc352a31533ffbcf4ef22c744658688086fc/data/benign-behaviors.csv",
    "strongreject-custom": f"{GH}/alexandrasouly/strongreject/f7cad6c17e624e21d8df2278e918ae1dddb4cb56/strongreject_dataset/strongreject_dataset.csv",
}

SOURCE_SET = {"jbb-harmful": "jbb-behaviors", "jbb-benign": "jbb-behaviors"}

TEST_MODELS = ["nemotron-3-super", "seed-oss-36b", "phi-4", "granite-4.2-8b"]
TRAIN_MODELS = ["qwen3-30b-a3b-2507", "mistral-small-3.2", "gemma-4-31b", "glm-4.5-air"]
OASST2_TEST_N = 1300      # pre-filter sample of benign first turns for v3
TRAIN_HARMFUL_TARGET = 3000
TRAIN_BENIGN_TARGET = 3000


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "AIRP-v3-build/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def csv_rows(b: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))


def row(set_name, sid, prompt, kind, **labels):
    r = {"id": f"{set_name}:{sid}", "prompt_set": set_name, "source_id": str(sid),
         "side": PROMPT_SET_SIDE[set_name], "kind": kind, "prompt": prompt}
    r.update({k: v for k, v in labels.items() if v not in (None, "")})
    return r


def build(raw: dict[str, bytes]) -> tuple[list[dict], dict]:
    notes: dict = {}
    rows: list[dict] = []
    # --- test side ---
    for r in csv_rows(raw["ailuminate-demo"]):
        rows.append(row("ailuminate-demo", r["release_prompt_id"], r["prompt_text"], "harmful",
                        hazard=r.get("hazard"), persona=r.get("persona")))
    for r in csv_rows(raw["simplesafetytests"]):
        rows.append(row("simplesafetytests", r["id"], r["prompt"], "harmful",
                        harm_area=r.get("harm_area"), category=r.get("category")))
    for r in csv_rows(raw["xstest"]):
        kind = "benign" if r["label"].strip() == "safe" else "harmful"
        rows.append(row("xstest", r["id"], r["prompt"], kind, type=r.get("type"),
                        label=r.get("label"), note=r.get("note")))
    msgs = [json.loads(l) for l in gzip.decompress(raw["oasst2-firstturn"]).decode("utf-8").split("\n") if l.strip()]
    firsts = [m for m in msgs if m.get("parent_id") is None and m.get("role") == "prompter"
              and m.get("lang") == "en" and not m.get("deleted") and m.get("review_result") is not False]
    firsts.sort(key=lambda m: m["message_id"])
    random.Random(SEED).shuffle(firsts)
    notes["oasst2_eligible_first_turns"] = len(firsts)
    for m in firsts[:OASST2_TEST_N]:
        rows.append(row("oasst2-firstturn", m["message_id"], m["text"], "benign"))
    # --- train side ---
    for r in csv_rows(raw["donotanswer"]):
        rows.append(row("donotanswer", r["id"], r["question"], "harmful",
                        types_of_harm=r.get("types_of_harm"), risk_area=r.get("risk_area")))
    hb = csv_rows(raw["harmbench-text"])
    notes["harmbench_functional_categories"] = dict(Counter(r["FunctionalCategory"] for r in hb))
    for r in hb:
        if r["FunctionalCategory"] != "standard":
            continue  # contextual rows need a context block prepended; copyright rows are not safety harms
        rows.append(row("harmbench-text", r["BehaviorID"], r["Behavior"], "harmful",
                        SemanticCategory=r.get("SemanticCategory")))
    for r in csv_rows(raw["jbb-harmful"]):
        rows.append(row("jbb-behaviors", "harmful-" + r["Index"], r["Goal"], "harmful", Category=r.get("Category")))
    for r in csv_rows(raw["jbb-benign"]):
        rows.append(row("jbb-behaviors", "benign-" + r["Index"], r["Goal"], "benign", Category=r.get("Category")))
    sr = csv_rows(raw["strongreject-custom"])
    notes["strongreject_sources"] = dict(Counter(r["source"] for r in sr))
    for i, r in enumerate(sr):
        if r["source"] != "custom":
            continue
        rows.append(row("strongreject-custom", f"row{i:03d}", r["forbidden_prompt"], "harmful", category=r.get("category")))
    aeg = json.loads(raw["aegis2-train"])
    if isinstance(aeg, dict):
        aeg = aeg.get("data") or aeg.get("rows") or list(aeg.values())[0]
    seen = set()
    aeg_ok = []
    redacted = 0
    for r in aeg:
        p = r.get("prompt") or ""
        if not p.strip() or p.strip().upper() == "REDACTED":
            redacted += 1
            continue
        k = normalize(p)
        if k in seen:
            continue
        seen.add(k)
        aeg_ok.append(r)
    notes["aegis_rows"] = len(aeg)
    notes["aegis_redacted_or_empty_skipped"] = redacted
    aeg_ok.sort(key=lambda r: str(r.get("id")))
    random.Random(SEED + 1).shuffle(aeg_ok)
    n_h = sum(1 for r in rows if r["side"] == "train" and r["kind"] == "harmful")
    n_b = sum(1 for r in rows if r["side"] == "train" and r["kind"] == "benign")
    need_h, need_b = TRAIN_HARMFUL_TARGET - n_h, TRAIN_BENIGN_TARGET - n_b
    for r in aeg_ok:
        lab = (r.get("prompt_label") or "").strip().lower()
        kind = "harmful" if lab == "unsafe" else "benign" if lab == "safe" else None
        if kind == "harmful" and need_h > 0:
            need_h -= 1
        elif kind == "benign" and need_b > 0:
            need_b -= 1
        else:
            continue
        vc = r.get("violated_categories")
        rows.append(row("aegis2-train", r["id"], r["prompt"], kind, violated_categories=vc))
    return rows, notes


def leak_drop(test: list[dict], train: list[dict]) -> tuple[list[dict], list[str]]:
    """Port of the leak.mjs rule: exact after normalisation, substring >=40 chars,
    word 4-gram Jaccard >= 0.5. Colliding TEST rows are dropped."""
    tr_norm = [normalize(r["prompt"]) for r in train]
    exact = set(tr_norm)
    grams = [word_ngrams(r["prompt"], 4) for r in train]
    inv: dict[str, list[int]] = {}
    for i, g in enumerate(grams):
        for x in g:
            inv.setdefault(x, []).append(i)
    long_train = [t for t in tr_norm if len(t) >= 40]
    keep, dropped = [], []
    for r in test:
        n = normalize(r["prompt"])
        hit = n in exact
        if not hit and len(n) >= 40:
            hit = any(n in t or t in n for t in long_train)
        if not hit:
            g = word_ngrams(r["prompt"], 4)
            cnt = Counter(i for x in g for i in inv.get(x, ()))
            for i, c in cnt.items():
                if c / (len(g) + len(grams[i]) - c) >= 0.5:
                    hit = True
                    break
        (dropped.append(r["id"]) if hit else keep.append(r))
    return keep, dropped


def dedupe(rows: list[dict]) -> tuple[list[dict], list[str]]:
    seen, keep, dropped = set(), [], []
    for r in rows:
        k = normalize(r["prompt"])
        if k in seen:
            dropped.append(r["id"])
            continue
        seen.add(k)
        keep.append(r)
    return keep, dropped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw, src = {}, {}
    for k, url in SOURCES.items():
        b = fetch(url)
        raw[k] = b
        src[k] = {"url": url, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
    rows, notes = build(raw)
    del raw
    by_side = {"test": [r for r in rows if r["side"] == "test"], "train": [r for r in rows if r["side"] == "train"]}
    pre = {s: dict(Counter(r["prompt_set"] for r in v)) for s, v in by_side.items()}
    results = {}
    for side in ("train", "test"):
        kept, rep = filter_rows(by_side[side])
        rep.pop("dropped", None)
        kept, dup = dedupe(kept)
        rep["n_dropped_duplicate"] = len(dup)
        rep["dropped_duplicate_ids"] = dup
        results[side] = [kept, rep]
    test_kept, leak = leak_drop(results["test"][0], results["train"][0])
    results["test"][0] = test_kept
    results["test"][1]["n_dropped_leak_vs_train"] = len(leak)
    results["test"][1]["dropped_leak_vs_train_ids"] = leak
    models = {"test": TEST_MODELS, "train": TRAIN_MODELS}
    summary = {"sources": src, "notes": notes, "seed": SEED}
    for side in ("test", "train"):
        kept, rep = results[side]
        kept.sort(key=lambda r: r["id"])
        random.Random(SEED + (7 if side == "test" else 11)).shuffle(kept)
        for i, r in enumerate(kept):
            r["assigned_model"] = models[side][i % len(models[side])]
        body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept)
        pf = out / f"prompts-{side}.jsonl"
        pf.write_text(body, encoding="utf-8")
        rep.update({
            "side": side,
            "n_kept_final": len(kept),
            "sources": {k: v for k, v in src.items() if PROMPT_SET_SIDE[SOURCE_SET.get(k, k)] == side},
            "pre_filter_counts_by_set": pre[side],
            "kept_counts_by_set": dict(Counter(r["prompt_set"] for r in kept)),
            "kept_counts_by_set_kind": dict(Counter(f'{r["prompt_set"]}/{r["kind"]}' for r in kept)),
            "kept_counts_by_model": dict(Counter(r["assigned_model"] for r in kept)),
            "dropped_counts_by_set": dict(Counter(i.split(":")[0] for i in rep["dropped_category_ids"] + rep["dropped_keyword_ids"])),
            "out_file": pf.name,
            "out_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "notes": notes,
            "seed": SEED,
            "wording_changed": False,
            "system_prompt": None,
            "template": None,
        })
        (out / f"filter-report-{side}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary[side] = {k: rep[k] for k in ("n_in", "n_dropped_category", "n_dropped_keyword", "n_dropped_duplicate", "n_kept_final", "kept_counts_by_set_kind", "kept_counts_by_model", "out_sha256")}
        if side == "test":
            summary[side]["n_dropped_leak_vs_train"] = rep["n_dropped_leak_vs_train"]
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
