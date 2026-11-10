"""Lap C: recall of the three models on malicious runs, counted by variant/PROTOCOL-C.md.

  python3 variant/score_mal.py --features lapc_features.csv [rerun...] --results lapc_results.csv [rerun...] --out lapc_scores.csv
"""
import argparse, os, re, sys, joblib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "src"))
sys.path.insert(0, HERE)
from extract import FEATURES
from preprocess import transform
from score import wilson

RAN = re.compile(r"Preparing metadata|Getting requirements to build wheel|Building wheel|metadata-generation-failed")
FAILED = re.compile(r"did not run successfully|metadata-generation-failed")
NOT_RAN = re.compile(r"requires a different Python|No matching distribution|Could not find a version")


def log_class(pkg):
    p = os.path.join(BASE, "traces", pkg, f"{pkg}_install_log.txt")
    try:
        t = open(p, errors="replace").read()
    except OSError:
        return "no log"
    if NOT_RAN.search(t):
        return "not run (python/version/download)"
    if RAN.search(t) and FAILED.search(t):
        return "build stage ran"
    return "other failure"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", nargs="+", required=True)
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", default="lapc_scores.csv")
    a = ap.parse_args()
    f = pd.concat([pd.read_csv(x) for x in a.features]).drop_duplicates("Package_Name", keep="last")
    r = pd.concat([pd.read_csv(x) for x in a.results]).drop_duplicates("Package_Name", keep="last")
    d = f.merge(r[["Package_Name", "Status", "Probe_Died", "Attach_Delay", "Install_Seconds"]], on="Package_Name")
    delay = pd.to_numeric(d.Attach_Delay, errors="coerce")
    secs = pd.to_numeric(d.Install_Seconds, errors="coerce")
    why = pd.Series("", index=d.index)
    why[d.Probe_Died.astype(str) != "none"] = "probe died"
    why[(why == "") & (delay > 10)] = "orphan pip (delay > 10 s)"
    why[(why == "") & secs.isna()] = "no install time (timeout)"
    for i in d.index[(why == "") & (d.Status != "Success")]:
        c = log_class(d.at[i, "Package_Name"])
        if c != "build stage ran":
            why[i] = "pip failed: " + c
    d["Excluded"] = why
    d["Success_only"] = d.Status == "Success"

    X = transform(d)
    names = ["RF_authors"]
    d["RF_authors"] = joblib.load(os.path.join(BASE, "models", "Random-Forest.pkl")).predict_proba(X[FEATURES])[:, 1].round(4)
    for v in ("drop_g1g2", "drop_g1g2g3"):
        var = joblib.load(os.path.join(HERE, f"rf_{v}.pkl"))
        d["RF_" + v] = var["model"].predict_proba(X[var["cols"]])[:, 1].round(4)
        names.append("RF_" + v)
    d[["Package_Name", "Status", "Probe_Died", "Attach_Delay", "Install_Seconds", "Excluded"] + names].to_csv(a.out, index=False)

    ok = d[d.Excluded == ""]
    print(f"traced {len(d)} | counted {len(ok)} (success {int(ok.Success_only.sum())}, "
          f"build-stage failures {int((~ok.Success_only).sum())}) | excluded {int((d.Excluded != '').sum())}")
    print(f"distinct feature vectors among counted: {len(ok.drop_duplicates(subset=FEATURES))}/{len(ok)}")
    for label, part in (("PRIMARY (protocol rule)", ok), ("secondary (success only)", ok[ok.Success_only])):
        print(label)
        for m in names:
            k = int((part[m] >= 0.5).sum())
            lo, hi = wilson(k, len(part))
            print(f"  {m:17s} recall {k}/{len(part)} = {k / max(len(part), 1):.1%} (95% CI {lo:.1%}-{hi:.1%})")
    print("excluded:")
    for _, x in d[d.Excluded != ""].iterrows():
        print(f"  {x.Package_Name}: {x.Excluded}")
    print(f"[+] per-package scores: {a.out}")


if __name__ == "__main__":
    main()
