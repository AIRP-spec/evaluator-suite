"""Write a derived copy of an already-collected JSONL with the 2026-11-01b flags.

The source file is never modified (its sha256 is checked before and after).
Each derived row gets the same fields new rows get at write time:
  provenance.truncated            finish_reason == "length"
  provenance.max_tokens_cap       the cap the row was collected under (sampling.max_tokens)
  provenance.reasoning_markers_stripped / original_content / empty_after_strip
and `content` has reasoning spans stripped by airp_v3.collect.strip_reasoning.

  python3 tools/flag_collected.py SRC.jsonl DST.jsonl
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from airp_v3.collect import strip_reasoning  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(src, dst):
    before = sha(src)
    n = trunc = stripped = empty = 0
    with open(dst, "w", encoding="utf-8") as out:
        for line in Path(src).read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            r = json.loads(line)
            pv = r["provenance"]
            original = r.get("content") or ""
            clean, markers = strip_reasoning(original)
            r["content"] = clean
            pv["thinking_markers_in_content"] = markers
            pv["reasoning_markers_stripped"] = bool(markers)
            pv["original_content"] = original if markers else None
            pv["empty_after_strip"] = bool(markers) and not clean
            pv["truncated"] = pv.get("finish_reason") == "length"
            pv["max_tokens_cap"] = (pv.get("sampling") or {}).get("max_tokens")
            pv["derived_from_sha256"] = before
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1; trunc += pv["truncated"]; stripped += bool(markers); empty += pv["empty_after_strip"]
    assert sha(src) == before, "source changed"
    print(json.dumps({"src": src, "src_sha256": before, "dst": dst, "dst_sha256": sha(dst), "rows": n,
                      "truncated": trunc, "markers_stripped": stripped, "empty_after_strip": empty}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
