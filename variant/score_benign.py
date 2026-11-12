"""Lap B: FPR of the three models on benign runs, with the exclusion rules of variant/PROTOCOL.md.

  python3 variant/score_benign.py --features fresh_features.csv fresh_rerun_features.csv \
      --results fresh_results.csv fresh_rerun_results.csv --out fresh_scores.csv

Last row per package wins, so pass the re-run files after the first run.
"""
import argparse, os, sys, joblib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "src"))
sys.path.insert(0, HERE)
from extract import FEATURES
from preprocess import transform
from score import load, wilson


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", nargs="+", required=True)
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", default="fresh_scores.csv")
    a = ap.parse_args()
    d = load(a.features, a.results, "benign")
    X = transform(d)
    names = ["RF_authors"]
    d["RF_authors"] = joblib.load(os.path.join(BASE, "models", "Random-Forest.pkl")).predict_proba(X[FEATURES])[:, 1].round(4)
    for v in ("drop_g1g2", "drop_g1g2g3"):
        var = joblib.load(os.path.join(HERE, f"rf_{v}.pkl"))
        d["RF_" + v] = var["model"].predict_proba(X[var["cols"]])[:, 1].round(4)
        names.append("RF_" + v)
    d[["Package_Name", "Status", "Probe_Died", "Attach_Delay", "Install_Seconds", "Excluded"] + names].to_csv(a.out, index=False)

    ok = d[d.Excluded == ""]
    print(f"valid benign runs: {len(ok)} (excluded {int((d.Excluded != '').sum())} of {len(d)})")
    for m in names:
        k = int((ok[m] >= 0.5).sum())
        lo, hi = wilson(k, len(ok))
        print(f"{m:17s} FPR {k}/{len(ok)} = {k / max(len(ok), 1):.1%} (95% CI {lo:.1%}-{hi:.1%})")
    secs = pd.to_numeric(ok.Install_Seconds, errors="coerce")
    for name, part in (("install < 5 s", ok[secs < 5]), ("install >= 5 s", ok[secs >= 5])):
        if len(part):
            print(f"  {name}: n={len(part)} | FP " + " | ".join(f"{m} {int((part[m] >= 0.5).sum())}" for m in names))
    print("excluded:")
    for _, r in d[d.Excluded != ""].iterrows():
        print(f"  {r.Package_Name}: {r.Excluded}")
    print(f"[+] per-package scores: {a.out}")


if __name__ == "__main__":
    main()
