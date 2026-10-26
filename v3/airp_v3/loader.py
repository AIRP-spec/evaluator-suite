"""Item loader with composition assertion.

expect_classes is always derived from expect_primitives via composition 2a.
If a row also stores expect_classes / expect / classes, the loader asserts
equality and refuses the file on mismatch (brief §4.3 / §4.4).
"""
from __future__ import annotations

import json
from pathlib import Path

from .compose import COMPOSITION_2A_SHA256, compose, load_composition, validate


class LoaderError(ValueError):
    pass


def _prims(row: dict) -> dict:
    if "expect_primitives" in row:
        p = row["expect_primitives"]
        return {"stance": p["stance"], "objects": list(p.get("objects") or []), "qualifiers": list(p.get("qualifiers") or [])}
    if "stance" in row:
        return {"stance": row["stance"], "objects": list(row.get("objects") or []), "qualifiers": list(row.get("qualifiers") or [])}
    raise LoaderError(f"row {row.get('id')!r} has no expect_primitives / stance")


def _stored_classes(row: dict) -> list[str] | None:
    for k in ("expect_classes", "expect", "classes"):
        if k in row and row[k] is not None:
            return list(row[k])
    return None


def load_items(path: Path | str, composition=None) -> list[dict]:
    comp = composition if composition is not None else load_composition(expect_sha256=COMPOSITION_2A_SHA256)
    out = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        prims = _prims(row)
        errs = validate(prims)
        if errs:
            raise LoaderError(f"{path}:{i} id={row.get('id')}: {errs}")
        derived = compose(prims, comp)
        stored = _stored_classes(row)
        if stored is not None and sorted(stored) != sorted(derived):
            raise LoaderError(
                f"{path}:{i} id={row.get('id')}: stored classes {stored} != composed {derived}"
            )
        out.append({
            **row,
            "expect_primitives": prims,
            "expect_classes": derived,
        })
    return out
