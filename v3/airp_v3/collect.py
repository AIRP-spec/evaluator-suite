"""Collection runner: public prompts -> model outputs.

Two backends:

* ``--backend openrouter`` (default, unchanged): DISABLED until a file named
  OPENROUTER_APPROVAL exists in the repo root (or --approval-file) containing
  Justin's written red-teaming approval (standing brief §4.2, OpenRouter ToS §7(11)/§8).
* ``--backend local``: a self-hosted vLLM OpenAI-compatible server (v3 plan
  amendment 2026-11-01). Does NOT read OPENROUTER_APPROVAL. Instead it refuses
  unless (a) POLICY_VERIFIED lists the model at its revision with a CLEAR verdict,
  the right role and the recorded license sha256 (airp_v3.policy.find_policy_verified),
  (b) the prompts file hashes to its filter_cse report, and (c) every prompt set
  belongs to the model's side. Thinking is forced off through the model entry's
  chat_template_kwargs and reasoning tokens are recorded. Runs concurrent requests,
  appends and resumes by id, and stops on a wall-clock or dollar limit.

  python3 -m airp_v3.collect --backend local --base-url http://127.0.0.1:8000 \
      --models collect/models.selfhost.json --model-key phi-4 --role test \
      --policy-file policy/POLICY_VERIFIED.json \
      --prompts prompts-test.jsonl --filter-report filter-report-test.json \
      --host runpod:<pod>/<gpu>/vllm-<ver> --out items-phi-4.jsonl \
      --concurrency 64 --max-wall-seconds 3000 --max-dollars 3 --dollars-per-hour 0.59

Per-row provenance: model, host, prompt_set, prompt_id, timestamp, token_counts,
provider_terms_ref.

  python3 -m airp_v3.collect --prompts kept.jsonl --models models.json \
      --prompt-set ailuminate-demo --out items.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OPENAI_PREFIXES = ("openai/", "~openai/")
DEFAULT_APPROVAL = "OPENROUTER_APPROVAL"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PROVIDER_TERMS_REF = "https://openrouter.ai/terms (checked 2026-10-19; red-teaming needs written approval)"


from .policy import CollectBlocked, check_prompts, find_policy_verified, sha256_path  # noqa: E402


def find_approval(path: Path) -> str:
    if not path.is_file():
        raise CollectBlocked(
            f"refusing to call OpenRouter: approval file not found at {path}. "
            "Collection waits for Justin's written OpenRouter red-teaming approval "
            "(standing brief §4.2). Place the approval text in OPENROUTER_APPROVAL."
        )
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 40:
        raise CollectBlocked(
            f"approval file {path} is too short to be Justin's written approval "
            f"({len(text)} chars). Refusing to collect."
        )
    low = text.lower()
    if "justin" not in low and "flores" not in low and "approved" not in low:
        raise CollectBlocked(
            f"approval file {path} does not look like Justin's written approval "
            "(expected to mention Justin/Flores/approved). Refusing to collect."
        )
    return text


def _forbid_openai(model_id: str) -> None:
    if model_id.startswith(OPENAI_PREFIXES) or "/openai/" in model_id:
        raise CollectBlocked(f"OpenAI models are forbidden: {model_id}")


def call_openrouter(model: str, host: str | None, prompt: str, api_key: str,
                    max_tokens: int = 800, temperature: float = 0.7) -> dict:
    _forbid_openai(model)
    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if host:
        body["provider"] = {"order": [host], "allow_fallbacks": False}
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/AIRP-spec/evaluator-suite",
            "X-Title": "AIRP evaluator-suite collection",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def collect_one(prompt_row: dict, model: str, host: str | None, prompt_set: str,
                api_key: str) -> dict:
    prompt_id = prompt_row.get("id") or prompt_row.get("prompt_id") or prompt_row.get("qid")
    text = None
    for f in ("prompt", "question", "behavior", "text", "content", "query", "input"):
        if isinstance(prompt_row.get(f), str) and prompt_row[f].strip():
            text = prompt_row[f]
            break
    if not text:
        raise ValueError(f"prompt {prompt_id!r} has no text field")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = call_openrouter(model, host, text, api_key)
    choice = (raw.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    usage = raw.get("usage") or {}
    return {
        "id": f"{prompt_set}:{prompt_id}:{model.replace('/', '_')}",
        "content": content,
        "provenance": {
            "model": model,
            "host": host or (raw.get("provider") or "unspecified"),
            "prompt_set": prompt_set,
            "prompt_id": str(prompt_id),
            "timestamp": ts,
            "token_counts": {
                "prompt": usage.get("prompt_tokens"),
                "completion": usage.get("completion_tokens"),
                "total": usage.get("total_tokens"),
            },
            "provider_terms_ref": PROVIDER_TERMS_REF,
            "openrouter_id": raw.get("id"),
        },
    }


def main(argv=None) -> int:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--backend", choices=("openrouter", "local"), default="openrouter")
    known, _ = pre.parse_known_args(argv)
    if known.backend == "local":
        return main_local(argv)
    return main_openrouter(argv)


def main_openrouter(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=("openrouter", "local"), default="openrouter")
    ap.add_argument("--prompts", required=True, help="filtered prompts JSONL")
    ap.add_argument("--models", required=True,
                    help='JSON list of {"model": "...", "host": "..."} (host optional)')
    ap.add_argument("--prompt-set", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--approval-file", default=None,
                    help=f"default: repo-root/{DEFAULT_APPROVAL}")
    ap.add_argument("--limit", type=int, default=0, help="optional cap for dry smoke")
    ap.add_argument("--sleep", type=float, default=0.2)
    a = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    approval_path = Path(a.approval_file) if a.approval_file else repo_root / DEFAULT_APPROVAL
    try:
        approval = find_approval(approval_path)
    except CollectBlocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 2

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("BLOCKED: OPENROUTER_API_KEY not set", file=sys.stderr)
        return 2

    models = json.loads(Path(a.models).read_text(encoding="utf-8"))
    for m in models:
        _forbid_openai(m["model"])

    prompts = []
    for line in Path(a.prompts).read_text(encoding="utf-8").splitlines():
        if line.strip():
            prompts.append(json.loads(line))
    if a.limit:
        prompts = prompts[: a.limit]

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for pr in prompts:
            for m in models:
                try:
                    row = collect_one(pr, m["model"], m.get("host"), a.prompt_set, api_key)
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8", errors="replace")
                    print(f"HTTP {e.code} on {m['model']}: {body[:200]}", file=sys.stderr)
                    return 1
                row["provenance"]["approval_sha256_prefix"] = (
                    __import__("hashlib").sha256(approval.encode()).hexdigest()[:16]
                )
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
                time.sleep(a.sleep)
    print(json.dumps({"n_written": n, "out": str(out_path), "approval_file": str(approval_path)}))
    return 0


# ---------------------------------------------------------------------------
# local backend (self-hosted vLLM)
# ---------------------------------------------------------------------------

THINK_MARKERS = ("<think>", "</think>", "<|channel>thought", "<seed:think>", "</seed:think>")


def _text_of(row: dict) -> str:
    for f in ("prompt", "question", "behavior", "text", "content", "query", "input"):
        if isinstance(row.get(f), str) and row[f].strip():
            return row[f]
    raise ValueError(f"prompt {row.get('id')!r} has no text field")


def call_local(base_url: str, served_model: str, prompt: str, max_tokens: int,
               temperature: float, chat_template_kwargs: dict, timeout: float = 600) -> dict:
    if "openrouter.ai" in base_url or "openai.com" in base_url:
        raise CollectBlocked(f"--backend local must point at a self-hosted server, not {base_url}")
    body = {
        "model": served_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if chat_template_kwargs:
        body["chat_template_kwargs"] = chat_template_kwargs
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def local_row(prompt_row: dict, model: dict, host: str, raw: dict, ts: str, ctx: dict) -> dict:
    choice = (raw.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    usage = raw.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    reasoning_tokens = details.get("reasoning_tokens")
    if reasoning_tokens is None:
        reasoning_tokens = 0 if not reasoning else None
    markers = [m for m in THINK_MARKERS if m in content]
    pid = str(prompt_row.get("id"))
    return {
        "id": f"{pid}::{model['key']}",
        "content": content,
        "reasoning_content": reasoning or None,
        "provenance": {
            "model": model["hf_id"],
            "model_key": model["key"],
            "revision": model["revision"],
            "quantization": model["quantization"],
            "role": model["role"],
            "host": host,
            "backend": "local-vllm",
            "prompt_set": prompt_row.get("prompt_set"),
            "prompt_id": pid,
            "prompt_kind": prompt_row.get("kind"),
            "timestamp": ts,
            "token_counts": {
                "prompt": usage.get("prompt_tokens"),
                "completion": usage.get("completion_tokens"),
                "total": usage.get("total_tokens"),
                "reasoning": reasoning_tokens,
            },
            "thinking_forced_off": ctx["chat_template_kwargs"],
            "thinking_markers_in_content": markers,
            "finish_reason": choice.get("finish_reason"),
            "sampling": {"temperature": ctx["temperature"], "max_tokens": ctx["max_tokens"],
                         "system_prompt": None, "template": "model chat template, single user turn"},
            "provider_terms_ref": model["terms_ref"],
            "license_sha256": ctx["license_sha256"],
            "policy_verified_sha256": ctx["policy_sha256"],
            "policy_verdict": ctx["verdict"],
            "prompts_sha256": ctx["prompts_sha256"],
            "response_id": raw.get("id"),
        },
    }


def load_done_ids(out_path: Path) -> set:
    done = set()
    if out_path.is_file():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                done.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue  # a torn last line from a killed run; the id is retried
    return done


def run_local(prompts: list[dict], model: dict, host: str, base_url: str, out_path: Path,
              ctx: dict, concurrency: int, max_wall_seconds: float, max_dollars: float,
              dollars_per_hour: float, billing_start: float, max_errors: int = 25,
              caller=call_local, clock=time.time) -> dict:
    import threading
    from concurrent.futures import ThreadPoolExecutor, FIRST_COMPLETED, wait

    done = load_done_ids(out_path)
    todo = [p for p in prompts if f"{p.get('id')}::{model['key']}" not in done]
    lock = threading.Lock()
    stats = {"n_skipped_resume": len(prompts) - len(todo), "n_written": 0, "n_errors": 0,
             "stop_reason": "complete", "errors": []}
    start = clock()
    err_path = out_path.with_suffix(".errors.jsonl")

    def over_limit() -> str | None:
        now = clock()
        if max_wall_seconds and now - start >= max_wall_seconds:
            return "wall_clock_limit"
        if max_dollars and dollars_per_hour and (now - billing_start) / 3600.0 * dollars_per_hour >= max_dollars:
            return "dollar_limit"
        if stats["n_errors"] >= max_errors:
            return "too_many_errors"
        return None

    def one(pr: dict):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        last = None
        for attempt in range(3):
            try:
                raw = caller(base_url, model["served_model"], _text_of(pr), ctx["max_tokens"],
                             ctx["temperature"], ctx["chat_template_kwargs"])
                return local_row(pr, model, host, raw, ts, ctx), None
            except CollectBlocked:
                raise
            except Exception as e:  # noqa: BLE001 - recorded per id, never silently
                last = f"{type(e).__name__}: {str(e)[:200]}"
                time.sleep(1 + attempt)
        return None, last

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=concurrency) as ex:
        it = iter(todo)
        pending = {}
        stop = None
        while True:
            while not stop and len(pending) < concurrency:
                stop = over_limit()
                if stop:
                    break
                pr = next(it, None)
                if pr is None:
                    break
                pending[ex.submit(one, pr)] = pr
            if not pending:
                break
            finished, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for f in finished:
                pr = pending.pop(f)
                row, err = f.result()
                with lock:
                    if row is not None:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                        fh.flush()
                        stats["n_written"] += 1
                    else:
                        stats["n_errors"] += 1
                        e = {"id": f"{pr.get('id')}::{model['key']}", "error": err}
                        stats["errors"].append(e)
                        with err_path.open("a", encoding="utf-8") as ef:
                            ef.write(json.dumps(e) + "\n")
            if stop is None:
                stop = over_limit()
        if stop:
            stats["stop_reason"] = stop
    stats["elapsed_seconds"] = round(clock() - start, 1)
    stats["n_remaining"] = len(todo) - stats["n_written"] - stats["n_errors"] if stats["stop_reason"] != "complete" else 0
    stats["errors"] = stats["errors"][:50]
    return stats


def main_local(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=("openrouter", "local"), required=True)
    ap.add_argument("--base-url", required=True, help="vLLM OpenAI-compatible server, e.g. http://127.0.0.1:8000")
    ap.add_argument("--models", required=True, help="collect/models.selfhost.json")
    ap.add_argument("--model-key", required=True)
    ap.add_argument("--role", required=True, choices=("test", "train"))
    ap.add_argument("--policy-file", required=True, help="policy/POLICY_VERIFIED.json")
    ap.add_argument("--prompts", required=True, help="filtered prompts JSONL (build_prompt_sets.py)")
    ap.add_argument("--filter-report", required=True, help="filter_cse report whose out_sha256 must match --prompts")
    ap.add_argument("--host", required=True, help="runpod:<pod>/<gpu>/vllm-<version>")
    ap.add_argument("--served-model", default=None, help="name the server serves (default: hf_id)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--assigned-only", action="store_true",
                    help="only rows whose assigned_model equals --model-key (round-robin split)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--max-tokens", type=int, default=800)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-wall-seconds", type=float, default=0)
    ap.add_argument("--max-dollars", type=float, default=0)
    ap.add_argument("--dollars-per-hour", type=float, default=0)
    ap.add_argument("--billing-start-epoch", type=float, default=0,
                    help="pod start (epoch s) so the dollar limit counts pod time before collection")
    ap.add_argument("--summary", default=None, help="write run summary JSON here")
    a = ap.parse_args(argv)
    try:
        if a.max_tokens > 800:
            raise CollectBlocked("max tokens is capped at 800 by the v3 plan")
        doc = json.loads(Path(a.models).read_text(encoding="utf-8"))
        models = {m["key"]: m for m in doc["models"]}
        if a.model_key not in models:
            raise CollectBlocked(f"model key {a.model_key!r} not in {a.models}")
        model = dict(models[a.model_key])
        _forbid_openai(model["hf_id"])
        if model.get("role") != a.role:
            raise CollectBlocked(f"{model['hf_id']} is a {model.get('role')} model; --role {a.role} refused")
        entry = find_policy_verified(Path(a.policy_file), model, a.role)
        rows = check_prompts(Path(a.prompts), Path(a.filter_report), a.role)
    except CollectBlocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 2
    if a.assigned_only:
        rows = [r for r in rows if r.get("assigned_model") == a.model_key]
    if a.limit:
        rows = rows[: a.limit]
    model["served_model"] = a.served_model or model["hf_id"]
    ctx = {
        "chat_template_kwargs": model.get("chat_template_kwargs") or {},
        "temperature": a.temperature,
        "max_tokens": a.max_tokens,
        "license_sha256": entry["license_sha256"],
        "verdict": entry["verdict"],
        "policy_sha256": sha256_path(Path(a.policy_file)),
        "prompts_sha256": sha256_path(Path(a.prompts)),
    }
    stats = run_local(rows, model, a.host, a.base_url, Path(a.out), ctx, a.concurrency,
                      a.max_wall_seconds, a.max_dollars, a.dollars_per_hour,
                      a.billing_start_epoch or time.time())
    stats.update({"model_key": a.model_key, "n_prompts_selected": len(rows), "out": a.out,
                  "host": a.host, "prompts_sha256": ctx["prompts_sha256"]})
    if a.summary:
        Path(a.summary).write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "errors"}))
    return 0 if stats["stop_reason"] == "complete" else 3


if __name__ == "__main__":
    sys.exit(main())
