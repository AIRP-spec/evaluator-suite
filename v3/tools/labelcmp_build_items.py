"""Build the labeler-comparison gold items from data-v9 val (pinned sha), box-local only.

Gold primitives are the row's adjudicated {stance, objects, qualifiers}; gold classes are
derived at load through composition 2a (sha-checked), never stored by hand.
writer_family: 'qwen' for path == 'writer' rows (writer Qwen2.5-32B-Instruct,
inference-advocate tools/evaluator-training/RUNBOOK.md), null for locally composed rows.
Writes items.jsonl (id, content, writer_family) and gold.jsonl (id, gold primitives,
derived classes, writer_family, kind). Prints counts and shas only.
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from airp_v3.compose import COMPOSITION_2A_SHA256, compose, load_composition, validate  # noqa: E402

VAL_SHA = "964c2b2198572823846364c7f30d4e6c44d8c9bf09fc59a0731f0ce7af7ecd2d"
src, outdir = Path(sys.argv[1]), Path(sys.argv[2])
raw = src.read_bytes()
assert hashlib.sha256(raw).hexdigest() == VAL_SHA, "val sha mismatch"
comp = load_composition(None, COMPOSITION_2A_SHA256)
outdir.mkdir(parents=True, exist_ok=True)
items, gold, dropped_nonvocab = [], [], []
for line in raw.decode().splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    full = {"stance": r["stance"], "objects": sorted(r["objects"]), "qualifiers": sorted(r["qualifiers"])}
    # 20 violence-kill-instruction rows carry the non-vocabulary object `criminal_assistance` (a class name, not
    # one of the 7 objects). It is dropped for primitive scoring; composition must be unchanged by the drop.
    g = {"stance": full["stance"], "objects": [o for o in full["objects"] if o != "criminal_assistance"],
         "qualifiers": full["qualifiers"]}
    if g != full:
        assert compose(g, comp) == compose(full, comp), r["id"]
        dropped_nonvocab.append(r["id"])
    assert not validate(g), (r["id"], validate(g))
    wf = "qwen" if r.get("path") == "writer" else None
    assert r.get("path") in ("writer", "composed"), r["id"]
    items.append({"id": r["id"], "content": r["content"], "writer_family": wf})
    gold.append({"id": r["id"], "gold": g, "classes": compose(g, comp), "writer_family": wf,
                 "kind": r.get("kind"), "contrastGroup": r.get("contrastGroup")})
assert len({x["id"] for x in items}) == len(items)
(outdir / "items.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items))
(outdir / "gold.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in gold))
from collections import Counter
c = Counter(k for x in gold for k in x["classes"])
print(json.dumps({"n": len(items), "nonvocab_object_dropped_rows": len(dropped_nonvocab), "writer_rows": sum(x["writer_family"] == "qwen" for x in items),
                  "class_positives": dict(sorted(c.items())),
                  "items_sha256": hashlib.sha256((outdir / "items.jsonl").read_bytes()).hexdigest(),
                  "gold_sha256": hashlib.sha256((outdir / "gold.jsonl").read_bytes()).hexdigest()}, indent=1))
