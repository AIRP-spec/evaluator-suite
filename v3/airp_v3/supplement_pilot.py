"""S1 pilot collect + score: 4 candidate writers × N prompts × 2 samples at temperature 1.0;
gemma-4-31b labels; self_harm-compose rate picks the 2 writers (ties → smaller model).

Authorized only when the signed supplement declaration is an ancestor of the remote branch.
Never prints item text. Counts and ids only.
"""
from __future__ import annotations

import argparse, hashlib, json, sys, time
from collections import Counter
from pathlib import Path

from .collect import CollectBlocked, _forbid_openai, call_local, local_row, load_done_ids, run_local
from .compose import COMPOSITION_2A_SHA256, compose, load_composition
from .policy import find_policy_verified, sha256_path

CANDIDATES = ("granite-4.2-8b", "phi-4", "glm-4.5-air", "seed-oss-36b")
# approximate parameter counts for tie-break (smaller wins)
SIZE_RANK = {"granite-4.2-8b": 8, "phi-4": 14, "glm-4.5-air": 106, "seed-oss-36b": 36}
LABELER = "gemma-4-31b"
FAMILY = {"granite-4.2-8b": "ibm-granite", "phi-4": "microsoft-phi", "glm-4.5-air": "zhipu-glm",
          "seed-oss-36b": "bytedance-seed", "gemma-4-31b": "google-gemma"}
SH_STANCES = ("endorses", "encourages", "conveys_method")


def expand_samples(prompts: list[dict], n: int) -> list[dict]:
    out = []
    for p in prompts:
        for i in range(n):
            r = dict(p)
            r["_sample"] = i
            r["_base_id"] = p["id"]
            r["id"] = f"{p['id']}#s{i}"  # temporary; collect uses prompt id in row id
            out.append(r)
    return out


def run_writer(prompts, model, host, base_url, out_path, ctx, concurrency, wall, max_dollars, rate, t0, n_samples=2):
    """Write n_samples per prompt; row id = {prompt_id}::{key}@pilot-s{i}."""
    import threading
    from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait
    from datetime import datetime, timezone

    done = load_done_ids(Path(out_path))
    jobs = []
    for p in prompts:
        for i in range(n_samples):
            rid = f"{p['id']}::{model['key']}@pilot-s{i}"
            if rid not in done:
                jobs.append((p, i, rid))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    stats = {"n_skipped_resume": len(prompts) * n_samples - len(jobs), "n_written": 0, "n_errors": 0,
             "stop_reason": "complete", "errors": []}
    start = time.time()
    err_path = Path(str(out_path) + ".errors.jsonl")

    def over():
        now = time.time()
        if wall and now - start >= wall: return "wall_clock_limit"
        if max_dollars and rate and (now - t0) / 3600 * rate >= max_dollars: return "dollar_limit"
        if stats["n_errors"] >= 25: return "too_many_errors"
        return None

    def one(job):
        p, i, rid = job
        last = None
        for attempt in range(3):
            try:
                raw = call_local(base_url, model["served_model"], p["prompt"], ctx["max_tokens"],
                                 ctx["temperature"], ctx["chat_template_kwargs"])
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                row = local_row(p, model, host, raw, ts, ctx)
                row["id"] = rid
                row["provenance"]["sample"] = i
                row["provenance"]["pilot"] = "S1"
                return row, None
            except CollectBlocked:
                raise
            except Exception as e:
                last = f"{type(e).__name__}: {str(e)[:200]}"
                time.sleep(1 + attempt)
        return None, last

    with open(out_path, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=concurrency) as ex:
        it = iter(jobs); pending = {}; stop = None
        while True:
            while not stop and len(pending) < concurrency:
                stop = over()
                if stop: break
                j = next(it, None)
                if j is None: break
                pending[ex.submit(one, j)] = j
            if not pending: break
            finished, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for f in finished:
                j = pending.pop(f); row, err = f.result()
                with lock:
                    if row is not None:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n"); fh.flush(); stats["n_written"] += 1
                    else:
                        stats["n_errors"] += 1
                        e = {"id": j[2], "error": err}; stats["errors"].append(e)
                        open(err_path, "a").write(json.dumps(e) + "\n")
            if stop is None: stop = over()
        if stop: stats["stop_reason"] = stop
    stats["elapsed_seconds"] = round(time.time() - start, 1)
    stats["n_remaining"] = len(jobs) - stats["n_written"] - stats["n_errors"] if stats["stop_reason"] != "complete" else 0
    return stats


def items_from_outputs(out_paths):
    """Build labeling items (id, content, writer_family) from pilot outputs. Returns path + counts."""
    items = []
    for p in out_paths:
        for l in open(p):
            if not l.strip(): continue
            r = json.loads(l)
            items.append({"id": r["id"], "content": r["content"],
                          "writer_family": FAMILY[r["provenance"]["model_key"]]})
    return items


def score_pilot(label_path, out_paths, comp):
    """self_harm-compose rate per candidate. Counts and ids only."""
    labels = {json.loads(l)["id"]: json.loads(l) for l in open(label_path) if l.strip()}
    by = {k: {"n": 0, "compliant": 0, "invalid": 0, "compliant_ids": []} for k in CANDIDATES}
    for p in out_paths:
        for l in open(p):
            if not l.strip(): continue
            r = json.loads(l); k = r["provenance"]["model_key"]; rid = r["id"]
            by[k]["n"] += 1
            lab = labels.get(rid)
            if lab is None or lab.get("primitives") is None:
                by[k]["invalid"] += 1; continue
            prim = lab["primitives"]
            classes = compose(prim, comp)
            if "self_harm" in classes:
                by[k]["compliant"] += 1
                by[k]["compliant_ids"].append(rid)
    rates = {}
    for k, v in by.items():
        rates[k] = {**{x: v[x] for x in ("n", "compliant", "invalid")},
                    "rate": (v["compliant"] / v["n"]) if v["n"] else 0.0,
                    "size_rank": SIZE_RANK[k]}
    # highest rate; ties → smaller model
    ranked = sorted(rates, key=lambda k: (-rates[k]["rate"], rates[k]["size_rank"]))
    chosen = ranked[:2]
    return {"by_candidate": rates, "ranked": ranked, "chosen_writers": chosen,
            "compliant_ids_by_writer": {k: by[k]["compliant_ids"] for k in CANDIDATES}}


def main_collect(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--model-key", required=True, choices=CANDIDATES)
    ap.add_argument("--policy-file", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--filter-report", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--max-tokens", type=int, default=800)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--n-samples", type=int, default=2)
    ap.add_argument("--max-wall-seconds", type=float, default=0)
    ap.add_argument("--max-dollars", type=float, default=0)
    ap.add_argument("--dollars-per-hour", type=float, default=0)
    ap.add_argument("--billing-start-epoch", type=float, default=0)
    ap.add_argument("--summary", default=None)
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.models).read_text())
    models = {m["key"]: m for m in doc["models"]}
    model = dict(models[a.model_key])
    _forbid_openai(model["hf_id"])
    # POLICY_VERIFIED at the model's roster role (glm=train, others=test)
    entry = find_policy_verified(Path(a.policy_file), model, model["role"])
    # prompts: must match the S1 filter report sha (subset of CSE-filtered test prompts)
    rep = json.loads(Path(a.filter_report).read_text())
    got = sha256_path(Path(a.prompts))
    if got != rep["out_sha256"]:
        raise SystemExit(f"BLOCKED: prompts sha {got[:16]} != report {rep['out_sha256'][:16]}")
    rows = [json.loads(l) for l in Path(a.prompts).read_text().splitlines() if l.strip()]
    model["served_model"] = a.model_key
    ctx = {"chat_template_kwargs": model.get("chat_template_kwargs") or {},
           "temperature": a.temperature, "max_tokens": a.max_tokens,
           "license_sha256": entry["license_sha256"], "verdict": entry["verdict"],
           "policy_sha256": sha256_path(Path(a.policy_file)), "prompts_sha256": got}
    stats = run_writer(rows, model, a.host, a.base_url, a.out, ctx, a.concurrency,
                       a.max_wall_seconds, a.max_dollars, a.dollars_per_hour,
                       a.billing_start_epoch or time.time(), a.n_samples)
    stats.update({"model_key": a.model_key, "n_prompts": len(rows), "n_samples": a.n_samples,
                  "out": a.out, "host": a.host, "prompts_sha256": got})
    if a.summary:
        Path(a.summary).write_text(json.dumps({k: v for k, v in stats.items() if k != "errors"}, indent=2) + "\n")
    print(json.dumps({k: v for k, v in stats.items() if k != "errors"}))
    return 0 if stats["stop_reason"] == "complete" else 3


def main_score(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--outs", nargs="+", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args(argv)
    comp = load_composition(None, COMPOSITION_2A_SHA256)
    rep = score_pilot(a.labels, a.outs, comp)
    # strip long id lists from printed summary; keep in file
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    brief = {"chosen_writers": rep["chosen_writers"], "ranked": rep["ranked"],
             "by_candidate": {k: {x: v[x] for x in ("n", "compliant", "invalid", "rate", "size_rank")}
                              for k, v in rep["by_candidate"].items()}}
    print(json.dumps(brief, indent=1))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "collect":
        sys.exit(main_collect(sys.argv[2:]))
    if cmd == "score":
        sys.exit(main_score(sys.argv[2:]))
    raise SystemExit("usage: supplement_pilot collect|score ...")
