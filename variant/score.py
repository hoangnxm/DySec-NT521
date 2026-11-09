"""Score traced packages with the authors' RF (36 cols) and the variant (drop G1+G2) side by side.

  python3 variant/score.py --benign ver_benign_features.csv --benign-results ver_benign_results.csv \
      --malicious ver_mal_features.csv --malicious-results ver_mal_results.csv --out ver_scores.csv

Runs left out (listed at the end): probe died, pip Failed, attach delay > 10 s (orphan pip), no install time.
Last row per package wins, so pass re-run files after the first run.
"""
import argparse, math, os, sys, joblib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "src"))
from extract import FEATURES
from preprocess import transform


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def load(feats, results, label):
    f = pd.concat([pd.read_csv(x) for x in feats]).drop_duplicates("Package_Name", keep="last")
    r = pd.concat([pd.read_csv(x) for x in results]).drop_duplicates("Package_Name", keep="last")
    d = f.merge(r[["Package_Name", "Status", "Probe_Died", "Attach_Delay", "Install_Seconds"]], on="Package_Name")
    delay = pd.to_numeric(d.Attach_Delay, errors="coerce")
    secs = pd.to_numeric(d.Install_Seconds, errors="coerce")
    why = pd.Series("", index=d.index)
    why[d.Probe_Died.astype(str) != "none"] = "probe died"
    why[(why == "") & (d.Status != "Success")] = "pip failed"
    why[(why == "") & (delay > 10)] = "orphan pip (delay > 10 s)"
    why[(why == "") & secs.isna()] = "no install time (timeout)"
    d["Excluded"] = why
    d["Class"] = label
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benign", nargs="+", required=True)
    ap.add_argument("--benign-results", nargs="+", required=True)
    ap.add_argument("--malicious", nargs="+", required=True)
    ap.add_argument("--malicious-results", nargs="+", required=True)
    ap.add_argument("--out", default="ver_scores.csv")
    a = ap.parse_args()

    d = pd.concat([load(a.benign, a.benign_results, "benign"),
                   load(a.malicious, a.malicious_results, "malicious")], ignore_index=True)
    X = transform(d)
    orig = joblib.load(os.path.join(BASE, "models", "Random-Forest.pkl"))
    var = joblib.load(os.path.join(HERE, "rf_drop_g1g2.pkl"))
    d["RF_authors"] = orig.predict_proba(X[FEATURES])[:, 1].round(4)
    d["RF_drop_G1G2"] = var["model"].predict_proba(X[var["cols"]])[:, 1].round(4)
    d[["Package_Name", "Class", "Status", "Probe_Died", "Attach_Delay", "Install_Seconds",
       "Excluded", "RF_authors", "RF_drop_G1G2"]].to_csv(a.out, index=False)

    ok = d[d.Excluded == ""]
    print(f"valid runs: benign {int((ok.Class == 'benign').sum())}, malicious {int((ok.Class == 'malicious').sum())}"
          f" (excluded {int((d.Excluded != '').sum())})")
    for m in ("RF_authors", "RF_drop_G1G2"):
        b, s = ok[ok.Class == "benign"], ok[ok.Class == "malicious"]
        fp, tp = int((b[m] >= 0.5).sum()), int((s[m] >= 0.5).sum())
        lo, hi = wilson(fp, len(b)); lo2, hi2 = wilson(tp, len(s))
        print(f"{m:13s} FPR {fp}/{len(b)} = {fp / max(len(b), 1):.1%} (95% CI {lo:.1%}-{hi:.1%})"
              f" | recall {tp}/{len(s)} = {tp / max(len(s), 1):.1%} (95% CI {lo2:.1%}-{hi2:.1%})")
    late = pd.to_numeric(ok.Attach_Delay, errors="coerce") >= 1.0
    for name, part in (("attach < 1.0 s", ok[~late]), ("attach >= 1.0 s", ok[late])):
        b = part[part.Class == "benign"]
        if len(b):
            print(f"  benign, {name}: n={len(b)} | FP authors {int((b.RF_authors >= 0.5).sum())}"
                  f" | FP variant {int((b.RF_drop_G1G2 >= 0.5).sum())}")
    if (d.Excluded != "").any():
        print("excluded:")
        for _, r in d[d.Excluded != ""].iterrows():
            print(f"  {r.Class:9s} {r.Package_Name}: {r.Excluded}")
    print(f"[+] per-package scores: {a.out}")


if __name__ == "__main__":
    main()
