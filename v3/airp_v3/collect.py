"""Collection runner: public prompts -> model outputs via OpenRouter.

DISABLED until a file named OPENROUTER_APPROVAL exists in the repo root (or the
path given by --approval-file) containing Justin's written red-teaming approval.
Refuses to call OpenRouter without it (standing brief §4.2, OpenRouter ToS §7(11)/§8).

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


class CollectBlocked(RuntimeError):
    pass


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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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


if __name__ == "__main__":
    sys.exit(main())
