"""Self-hosted collection gates (v3 plan amendment, 2026-11-01).

find_policy_verified(): a model may be collected from only if POLICY_VERIFIED lists
it (same HF id and revision), its verdict is CLEAR or CLEAR-WITH-CONDITIONS, its role
matches the requested role, and the license document on disk still has the recorded
sha256 (and the model entry carries the same sha256).

check_prompts(): the prompts file must hash to the `out_sha256` in its filter_cse
report, and every row's prompt set must belong to the model's side (test prompt
sets never go to training models, and the reverse).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ALLOWED_VERDICTS = ("CLEAR", "CLEAR-WITH-CONDITIONS")

# PR #34 split (docs/RED-TEAM-PROMPT-SETS.md "Suggested split"), plus one general
# instruction set per side for benign prompts: OASST2 first turns on test, the
# Aegis 2.0 `safe` prompts and JBB benign behaviors on train.
PROMPT_SET_SIDE = {
    "ailuminate-demo": "test",
    "simplesafetytests": "test",
    "xstest": "test",
    "oasst2-firstturn": "test",
    "aegis2-train": "train",
    "donotanswer": "train",
    "harmbench-text": "train",
    "jbb-behaviors": "train",
    "strongreject-custom": "train",
}


class CollectBlocked(RuntimeError):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def load_policy(policy_path: Path) -> dict:
    policy_path = Path(policy_path)
    if not policy_path.is_file():
        raise CollectBlocked(f"POLICY_VERIFIED not found at {policy_path}; refusing to collect")
    try:
        doc = json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CollectBlocked(f"POLICY_VERIFIED {policy_path} is not valid JSON: {e}") from e
    if not isinstance(doc.get("models"), list) or not doc["models"]:
        raise CollectBlocked(f"POLICY_VERIFIED {policy_path} lists no models")
    return doc


def find_policy_verified(policy_path: Path, model: dict, role: str | None = None) -> dict:
    """Return the POLICY_VERIFIED entry for `model` or raise CollectBlocked.

    `model` is a collection model entry: hf_id, revision, role, license_sha256.
    """
    policy_path = Path(policy_path)
    doc = load_policy(policy_path)
    hf_id, rev = model.get("hf_id"), model.get("revision")
    role = role or model.get("role")
    for ex in doc.get("excluded", []):
        if ex.get("hf_id") == hf_id:
            raise CollectBlocked(f"{hf_id} is excluded in POLICY_VERIFIED (verdict {ex.get('verdict')}): {ex.get('reason')}")
    hits = [e for e in doc["models"] if e.get("hf_id") == hf_id]
    if not hits:
        raise CollectBlocked(f"{hf_id} is not listed in POLICY_VERIFIED; refusing to collect")
    entry = next((e for e in hits if e.get("revision") == rev), None)
    if entry is None:
        raise CollectBlocked(f"{hf_id}@{rev} is not the verified revision ({[e.get('revision') for e in hits]}); refusing")
    verdict = entry.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        raise CollectBlocked(f"{hf_id} verdict is {verdict!r}, not CLEAR; refusing (doubt about terms: report, don't run)")
    if role not in ("test", "train"):
        raise CollectBlocked(f"role must be 'test' or 'train', got {role!r}")
    if entry.get("role") != role or model.get("role") not in (None, role):
        raise CollectBlocked(f"{hf_id} is verified for role {entry.get('role')!r}, requested {role!r}; refusing")
    lic_dir = policy_path.parent / doc.get("license_dir", "licenses")
    lic = lic_dir / entry["license_doc"]
    if not lic.is_file():
        raise CollectBlocked(f"license document {lic} missing; refusing")
    actual = sha256_path(lic)
    if actual != entry.get("license_sha256"):
        raise CollectBlocked(f"license sha256 mismatch for {hf_id}: file {actual[:16]} != recorded {str(entry.get('license_sha256'))[:16]}; refusing")
    if model.get("license_sha256") and model["license_sha256"] != entry["license_sha256"]:
        raise CollectBlocked(f"model entry license_sha256 for {hf_id} differs from POLICY_VERIFIED; refusing")
    return entry


def check_prompts(prompts_path: Path, report_path: Path, role: str) -> list[dict]:
    """Return prompt rows if the file matches its filter report and side; else raise."""
    prompts_path, report_path = Path(prompts_path), Path(report_path)
    if not report_path.is_file():
        raise CollectBlocked(f"filter_cse report {report_path} not found; refusing (prompts must be filtered first)")
    rep = json.loads(report_path.read_text(encoding="utf-8"))
    want = rep.get("out_sha256")
    got = sha256_path(prompts_path)
    if not want or got != want:
        raise CollectBlocked(f"prompts file sha256 {got[:16]} does not match filter_cse report out_sha256 {str(want)[:16]}; refusing")
    rows = [json.loads(l) for l in prompts_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        ps = r.get("prompt_set")
        side = PROMPT_SET_SIDE.get(ps)
        if side is None:
            raise CollectBlocked(f"row {r.get('id')}: unknown prompt set {ps!r}; refusing")
        if side != role or r.get("side", side) != role:
            raise CollectBlocked(f"row {r.get('id')}: prompt set {ps!r} belongs to the {side} side, model role is {role}; refusing")
    return rows
