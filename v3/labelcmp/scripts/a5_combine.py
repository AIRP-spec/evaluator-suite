"""AMENDMENT-5 combine: train queue -> decisions (majority of nemotron, seed-oss, guide-reader) + agreement with the
earlier 585 agent decisions. Reads labels and ids only; never reads item text."""
import argparse, collections, hashlib, json, sys
sys.path.insert(0, __file__.rsplit("/labelcmp/", 1)[0])
from airp_v3.xside import A5_DROP_UNREAD, decide_train_a5
from airp_v3.compose import COMPOSITION_2A_SHA256, compose, load_composition


def load(p):
    d = {}
    for l in open(p):
        if l.strip():
            r = json.loads(l); d[r["id"]] = r.get("primitives")
    return d


def main():
    ap = argparse.ArgumentParser()
    for a in ("--queue", "--primary", "--second", "--reader", "--old", "--out", "--drops", "--report"): ap.add_argument(a, required=True)
    a = ap.parse_args()
    comp = load_composition(None, COMPOSITION_2A_SHA256)
    q = [json.loads(l) for l in open(a.queue) if l.strip()]
    P, S, R = load(a.primary), load(a.second), load(a.reader)
    old = {x["n"]: x for x in json.load(open(a.old))}
    out, drops, rows = [], [], {}
    for n, r in enumerate(q):
        i = r["id"]
        if n in A5_DROP_UNREAD or r.get("cse_fire"):
            d = {"status": "dropped", "drop_reason": "cse_risk_unread_not_sent" if n in A5_DROP_UNREAD else "cse_fire_unread_not_sent"}
        elif i not in R:
            d = {"status": "dropped", "drop_reason": "reader_missing"}
        else:
            p, s, g = (x.get(i) for x in (P, S, R))
            d = decide_train_a5(p, s, g, comp)
        d = {"n": n, "id": i, "trigger": r.get("trigger") or r.get("reasons"), **d}
        rows[n] = d; out.append(d)
        if d["status"] == "dropped": drops.append((n, i, d["drop_reason"]))
    with open(a.out, "w") as f:
        for d in out: f.write(json.dumps(d, sort_keys=True) + "\n")
    with open(a.drops, "w") as f:
        f.write("n\tid\treason\n" + "".join(f"{n}\t{i}\t{r}\n" for n, i, r in drops))
    dec = [d for d in out if d["status"] == "decided"]
    by_class = collections.Counter(c for d in dec for c in d["final_classes"])
    agree_with = collections.Counter()
    for d in dec:
        cl = d["classes_by_labeler"]
        for k, c in zip(("primary", "second", "reader"), cl):
            if c is not None and c == d["final_classes"]: agree_with[k] += 1
    trio = collections.Counter(" | ".join(",".join(c) if c is not None else "INVALID" for c in d["classes_by_labeler"])
                               for d in out if d.get("classes_by_labeler") and len({tuple(c) if c is not None else None for c in d["classes_by_labeler"]}) > 1)
    # agreement with earlier 585 agent decisions
    cmp = collections.Counter(); per_cls = collections.defaultdict(collections.Counter); shapes = collections.Counter(); prim = collections.Counter()
    for n, o in old.items():
        nd = rows[n]
        if "final" not in o: cmp["old_skipped"] += 1; continue
        if nd["status"] != "decided": cmp[f"new_dropped:{nd['drop_reason']}"] += 1; continue
        oc, nc = sorted(o["classes"]), nd["final_classes"]
        cmp["compared"] += 1; cmp["agree" if oc == nc else "disagree"] += 1
        prim["exact_primitives_agree" if {**o["final"], "objects": sorted(o["final"]["objects"]), "qualifiers": sorted(o["final"]["qualifiers"])} == nd["final_primitives"] else "primitives_differ"] += 1
        for c in set(oc) | set(nc):
            per_cls[c]["both" if c in oc and c in nc else "old_only" if c in oc else "new_only"] += 1
        if oc != nc: shapes[f"old[{','.join(oc) or 'none'}] -> new[{','.join(nc) or 'none'}]"] += 1
    rep = {"amendment": "AMENDMENT-5", "queue_rows": len(q), "sent_to_reader": len(q) - sum(1 for _, _, r in drops if r.endswith("not_sent")),
           "reader_rows": len(R), "reader_valid": sum(1 for v in R.values() if v is not None),
           "outcome": dict(collections.Counter(d["status"] if d["status"] == "dropped" else "decided:" + d["trace"][0] for d in out)),
           "decided": len(dec), "dropped": len(drops), "drop_reasons": dict(collections.Counter(r for _, _, r in drops)),
           "drops_by_id": [{"n": n, "id": i, "reason": r} for n, i, r in drops],
           "hp_trace": dict(collections.Counter(t.split(":")[0] + ":" + t.split(":")[1] for d in dec for t in d["trace"] if t.startswith("hp_"))),
           "final_by_class": dict(sorted(by_class.items())), "final_no_class": sum(1 for d in dec if not d["final_classes"]),
           "final_agrees_with_labeler_classes": dict(agree_with), "trio_disagreement_shapes_top5": trio.most_common(5),
           "vs_old_585": dict(cmp), "vs_old_primitives": dict(prim), "vs_old_by_class": {c: dict(v) for c, v in sorted(per_cls.items())},
           "vs_old_disagreement_shapes_top5": shapes.most_common(5),
           "sha256": {k: hashlib.sha256(open(getattr(a, k), "rb").read()).hexdigest() for k in ("queue", "primary", "second", "reader", "old", "out")}}
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("decided", "dropped", "drop_reasons", "vs_old_585")}))


if __name__ == "__main__":
    main()
