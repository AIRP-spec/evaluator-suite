"""Self-hosted labeler pass (labeler comparison 2026-11-01; cross-side labeling later).

One labeler model served by vLLM (OpenAI-compatible) labels a set of items with the
same system prompt as airp_v3.label (SYSTEM_PREFIX + the FULL labeling guide, no
truncation), temperature 0, {stance, objects, qualifiers} output.

Gates (refuses before any request):
  * the labeler entry must pass airp_v3.policy.find_policy_verified at its verified
    revision and role (CLEAR / CLEAR-WITH-CONDITIONS, license sha256 on disk);
  * no OpenAI model, and the base URL must not be a hosted API;
  * an item whose writer family equals the labeler family is never sent (it is
    recorded as skipped_same_family). Items carry `writer_family` (null = locally
    composed, no writer model).

  python3 -m airp_v3.label_local --base-url http://127.0.0.1:18001 \
      --labelers labelcmp/labelers.labelcmp.json --labeler-key gemma-4-31b \
      --models collect/models.selfhost.json --policy-file policy/POLICY_VERIFIED.json \
      --guide LABELING-GUIDE.md --items items.jsonl --out labels-gemma-4-31b.jsonl \
      --host runpod:<pod>/<gpu>/vllm-<ver> --concurrency 64 --max-wall-seconds 900

Output rows: {id, labeler, family, primitives|null, error|null, meta{host, model,
revision, timestamp, token_counts, raw_text}}. No item text is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .collect import strip_reasoning
from .label import SYSTEM_PREFIX, _extract_json, _normalise_label
from .policy import CollectBlocked, find_policy_verified

OPENAI_MARKERS = ("openai/", "openai.com", "gpt-")


def build_messages(guide: str, content: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PREFIX + "\n\n# Labeling guide\n\n" + guide},
        {"role": "user", "content": "Label this assistant response:\n\n<<<\n" + content + "\n>>>"},
    ]


def gate(labeler: dict, model: dict, policy_file: Path, base_url: str) -> dict:
    for s in (labeler.get("key", ""), model.get("hf_id", ""), labeler.get("family", "")):
        if any(m in s.lower() for m in OPENAI_MARKERS):
            raise CollectBlocked(f"OpenAI models are forbidden: {s}")
    if any(h in base_url for h in ("openrouter.ai", "openai.com")):
        raise CollectBlocked(f"labeler base URL must be self-hosted, not {base_url}")
    if model["hf_id"] != labeler["hf_id"] or model["revision"] != labeler["revision"]:
        raise CollectBlocked(f"labeler {labeler['key']} pin differs from the collection model entry")
    return find_policy_verified(policy_file, model, role=model["role"])


def call(base_url: str, served: str, messages: list, max_tokens: int, ctk: dict, timeout: float = 300) -> dict:
    body = {"model": served, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if ctk:
        body["chat_template_kwargs"] = ctk
    req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def label_one(item: dict, labeler: dict, model: dict, guide: str, base_url: str, host: str, max_tokens: int) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {"id": item["id"], "labeler": labeler["key"], "family": labeler["family"], "primitives": None, "error": None,
           "meta": {"host": host, "model": model["hf_id"], "revision": model["revision"], "timestamp": ts}}
    last = None
    for attempt in range(3):
        try:
            raw = call(base_url, labeler["key"], build_messages(guide, item["content"]), max_tokens,
                       model.get("chat_template_kwargs") or {})
            ch = (raw.get("choices") or [{}])[0]
            text = (ch.get("message") or {}).get("content") or ""
            text, markers = strip_reasoning(text)
            u = raw.get("usage") or {}
            row["meta"].update({"token_counts": {"prompt": u.get("prompt_tokens"), "completion": u.get("completion_tokens")},
                                "finish_reason": ch.get("finish_reason"), "raw_text": text[:2000], "markers_stripped": markers})
            row["primitives"] = _normalise_label(_extract_json(text))
            row["error"] = None
            return row
        except Exception as e:  # noqa: BLE001 - recorded per row, never silent
            last = f"{type(e).__name__}: {str(e)[:300]}"
            row["error"] = last
            if isinstance(e, (ValueError, json.JSONDecodeError)):
                break  # deterministic at temperature 0; do not resample
            time.sleep(2 * (attempt + 1))
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--labelers", required=True)
    ap.add_argument("--labeler-key", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--policy-file", required=True)
    ap.add_argument("--guide", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--max-wall-seconds", type=float, default=1200)
    a = ap.parse_args(argv)
    labelers = {L["key"]: L for L in json.loads(Path(a.labelers).read_text())["labelers"]}
    labeler = labelers[a.labeler_key]
    model = {m["key"]: m for m in json.loads(Path(a.models).read_text())["models"]}[a.labeler_key]
    try:
        gate(labeler, model, Path(a.policy_file), a.base_url)
    except CollectBlocked as e:
        print(json.dumps({"blocked": str(e)}))
        return 2
    guide = Path(a.guide).read_text(encoding="utf-8")
    items = [json.loads(l) for l in Path(a.items).read_text(encoding="utf-8").splitlines() if l.strip()]
    send = [it for it in items if it.get("writer_family") != labeler["family"]]
    skipped = [it["id"] for it in items if it.get("writer_family") == labeler["family"]]
    t0 = time.time()
    out = []
    with ThreadPoolExecutor(a.concurrency) as ex:
        futs = [ex.submit(label_one, it, labeler, model, guide, a.base_url, a.host, a.max_tokens) for it in send]
        for f in as_completed(futs):
            out.append(f.result())
            if time.time() - t0 > a.max_wall_seconds:
                for g in futs:
                    g.cancel()
                break
    out.sort(key=lambda r: r["id"])
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    summ = {"labeler": labeler["key"], "n_items": len(items), "n_sent": len(send), "n_written": len(out),
            "n_valid": sum(r["primitives"] is not None for r in out), "n_error": sum(r["primitives"] is None for r in out),
            "skipped_same_family": skipped, "elapsed_seconds": round(time.time() - t0, 1),
            "guide_sha256": hashlib.sha256(guide.encode()).hexdigest(),
            "items_sha256": hashlib.sha256(Path(a.items).read_bytes()).hexdigest(),
            "out_sha256": hashlib.sha256(Path(a.out).read_bytes()).hexdigest()}
    print(json.dumps(summ))
    return 0 if len(out) == len(send) else 3


if __name__ == "__main__":
    sys.exit(main())
