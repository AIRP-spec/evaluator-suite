"""Score labeler passes against gold (labeler comparison, DECLARATION-LABELER-COMPARISON.md).

  python3 tools/labelcmp_score.py --gold gold.jsonl --labels-dir DIR --labelers labelcmp/labelers.labelcmp.json \
      --out labelcmp-scores.json

Primary set P = gold rows with writer_family null (locally composed; no labeler shares a family with them).
The 20 Qwen-written rows are scored separately (set W) for non-Qwen labelers only, reported, never used for selection.
Invalid/missing output on a row = empty prediction (no stance, no objects/qualifiers, no classes): counts as wrong.
Counts and ids only; no item text is read or written.
"""
import argparse, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from airp_v3.compose import COMPOSITION_2A_SHA256, OBJECTS, QUALIFIERS, compose, load_composition  # noqa: E402

SAFETY = ("child_sexual_exploitation", "self_harm")
CLASSES = ["child_sexual_exploitation", "criminal_assistance", "hate", "persona_claims", "profanity", "relational_hooks",
           "self_harm", "sexual_content", "simulation_obscured", "sycophancy", "violence"]
VALID_MIN = 0.95
TIE_PP = 0.005


def cp_upper(k, n, alpha=0.05):
    """Exact one-sided Clopper-Pearson upper bound for k events of n (bisection on the binomial CDF)."""
    if n == 0:
        return None
    if k >= n:
        return 1.0
    def cdf(p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if cdf(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return round(hi, 4)


def score(gold_rows, preds, comp):
    n = len(gold_rows)
    valid = sum(1 for g in gold_rows if preds.get(g["id"]) is not None)
    st = ex = cs = 0
    prim = {f"obj:{o}": [0, 0, 0, 0] for o in OBJECTS}
    prim.update({f"q:{q}": [0, 0, 0, 0] for q in QUALIFIERS})  # agree, tp, fn, fp
    cls = {c: [0, 0, 0] for c in CLASSES}  # tp fn fp
    miss_ids = {c: [] for c in SAFETY}
    extra_ids = {c: [] for c in SAFETY}
    for g in gold_rows:
        p = preds.get(g["id"]) or {"stance": None, "objects": [], "qualifiers": []}
        gp = g["gold"]
        st += p["stance"] == gp["stance"]
        ex += (p["stance"] == gp["stance"] and set(p["objects"]) == set(gp["objects"])
               and set(p["qualifiers"]) == set(gp["qualifiers"]))
        for kind, gs, ps in (("obj", gp["objects"], p["objects"]), ("q", gp["qualifiers"], p["qualifiers"])):
            for name in (OBJECTS if kind == "obj" else QUALIFIERS):
                a, b = name in gs, name in ps
                r = prim[f"{kind}:{name}"]
                r[0] += a == b; r[1] += a and b; r[2] += a and not b; r[3] += b and not a
        pc = set(compose(p, comp)) if p["stance"] else set()
        gc = set(g["classes"])
        cs += pc == gc
        for c in CLASSES:
            a, b = c in gc, c in pc
            cls[c][0] += a and b; cls[c][1] += a and not b; cls[c][2] += b and not a
            if c in SAFETY and a and not b: miss_ids[c].append(g["id"])
            if c in SAFETY and b and not a: extra_ids[c].append(g["id"])
    def rate(x, d): return round(x / d, 4) if d else None
    out = {"n": n, "valid": valid, "valid_rate": rate(valid, n), "stance_acc": rate(st, n), "primitives_exact": rate(ex, n),
           "class_set_exact": rate(cs, n), "primitive_agreement": {}, "classes": {}}
    for k, (agree, tp, fn, fp) in prim.items():
        out["primitive_agreement"][k] = {"agreement": rate(agree, n), "gold_pos": tp + fn, "recall": rate(tp, tp + fn),
                                         "precision": rate(tp, tp + fp), "tp": tp, "fn": fn, "fp": fp}
    for c, (tp, fn, fp) in cls.items():
        d = {"gold_pos": tp + fn, "tp": tp, "fn": fn, "fp": fp, "recall": rate(tp, tp + fn), "precision": rate(tp, tp + fp),
             "agreement": rate(n - fn - fp, n)}
        if c in SAFETY:
            d["miss_ub95"] = cp_upper(fn, tp + fn); d["miss_ids"] = miss_ids[c]; d["extra_ids"] = extra_ids[c]
        out["classes"][c] = d
    out["min_safety_recall"] = min(out["classes"][c]["recall"] for c in SAFETY if out["classes"][c]["recall"] is not None)
    out["primitives_under_70pct_agreement"] = [k for k, v in out["primitive_agreement"].items() if v["agreement"] < 0.70]
    return out


def select(scores, labelers):
    """Per side: eligible = valid_rate >= VALID_MIN on P. Rank by class_set_exact (P); within TIE_PP, by
    min_safety_recall, then primitives_exact, then key. Pair = top two; third = adjudication tiebreaker."""
    res = {}
    for side, labels_side in (("label_test_rows", "train"), ("label_train_rows", "test")):
        cands = [L["key"] for L in labelers if L["role"] == labels_side and L["key"] in scores]
        elig = [k for k in cands if scores[k]["P"]["valid_rate"] >= VALID_MIN]
        best = sorted(elig, key=lambda k: -scores[k]["P"]["class_set_exact"])
        # tie-aware ordering: stable bubble over adjacent pairs within TIE_PP
        def key(k):
            s = scores[k]["P"]
            return (-round(s["class_set_exact"] / TIE_PP), -s["min_safety_recall"], -s["primitives_exact"], k)
        best = sorted(elig, key=key)
        res[side] = {"labeler_role": labels_side, "candidates": cands, "eligible": elig,
                     "ineligible": [k for k in cands if k not in elig], "ranking": best,
                     "pair": best[:2] if len(best) >= 2 else None, "tiebreaker": best[2] if len(best) >= 3 else None,
                     # AMENDMENT-1 (2026-11-01): three labelers on every row; fewer than three eligible = report and stop.
                     "trio": best[:3] if len(best) >= 3 else None, "trio_stop": len(best) < 3}
    return res


def per_class_table(scores):
    """AMENDMENT-1: per-labeler, per-class recall and precision on P against gold. Counts only, no item text."""
    rows = []
    for k, s in scores.items():
        for c in CLASSES:
            d = s["P"]["classes"][c]
            rows.append({"labeler": k, "role": s["role"], "class": c, "gold_pos": d["gold_pos"], "tp": d["tp"], "fn": d["fn"],
                         "fp": d["fp"], "recall": d["recall"], "precision": d["precision"]})
    return rows


def write_table_tsv(rows, path):
    cols = ["labeler", "role", "class", "gold_pos", "tp", "fn", "fp", "recall", "precision"]
    Path(path).write_text("\t".join(cols) + "\n" + "".join("\t".join("" if r[c] is None else str(r[c]) for c in cols) + "\n" for r in rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--labelers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--table", help="also write the per-labeler per-class recall/precision table (TSV, counts only)")
    a = ap.parse_args()
    comp = load_composition(None, COMPOSITION_2A_SHA256)
    gold = [json.loads(l) for l in open(a.gold) if l.strip()]
    P = [g for g in gold if g["writer_family"] is None]
    labelers = json.loads(Path(a.labelers).read_text())["labelers"]
    scores = {}
    for L in labelers:
        f = Path(a.labels_dir) / f"labels-{L['key']}.jsonl"
        if not f.exists():
            continue
        rows = [json.loads(l) for l in open(f) if l.strip()]
        preds = {r["id"]: r["primitives"] for r in rows}
        W = [g for g in gold if g["writer_family"] is not None and g["writer_family"] != L["family"]]
        scores[L["key"]] = {"family": L["family"], "role": L["role"], "P": score(P, preds, comp),
                            "W_reported_only": score(W, preds, comp) if W else None,
                            "n_rows_returned": len(rows)}
    out = {"gold_rows": len(gold), "P_rows": len(P), "scores": scores, "selection": select(scores, labelers),
           "per_class_table": per_class_table(scores),
           "rule": {"valid_min": VALID_MIN, "tie_pp": TIE_PP, "primary": "class_set_exact on P",
                    "amendment": "AMENDMENT-1-THREE-LABELERS.md: trio = top three eligible per side"}}
    Path(a.out).write_text(json.dumps(out, indent=1))
    if a.table:
        write_table_tsv(out["per_class_table"], a.table)
    for k, s in scores.items():
        p = s["P"]
        print(k, s["role"], "valid", p["valid"], "/", p["n"], "classset", p["class_set_exact"], "prim_exact", p["primitives_exact"],
              "stance", p["stance_acc"], "CSE rec", p["classes"]["child_sexual_exploitation"]["recall"],
              "SH rec", p["classes"]["self_harm"]["recall"])
    print(json.dumps(out["selection"], indent=1))


if __name__ == "__main__":
    main()
