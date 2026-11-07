import argparse, os, sys, subprocess
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract, FEATURES
from predict import load_models, predict_pkg, show

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(BASE, "src", "scripts", "trace.sh")


def trace(pkg, duration):
    cmd = ["bash", SCRIPT, pkg, str(duration)]
    res = subprocess.run(cmd, cwd=BASE)
    return res.returncode == 0


def save(row, path):
    cols = ["Package_Name"] + FEATURES
    pd.DataFrame([row])[cols].to_csv(path, index=False)


def run(pkg, duration, out, skip, pipeline="repo"):
    if not skip:
        if os.name != "nt" and os.geteuid() != 0:
            print("Error: Must run with sudo to capture eBPF traces.")
            sys.exit(1)
        ok = trace(pkg, duration)
        if not ok:
            print("Error: Trace failed.")
            sys.exit(1)

    # trace.sh stores a local archive under its base name (traces/<name>, outputs/<name>)
    name = os.path.basename(pkg.rstrip("/"))
    if not os.path.isdir(os.path.join(BASE, "traces", name)):
        print(f"Error: No trace found in traces/{name}")
        sys.exit(1)
    row = extract(BASE, name)
    out = out or os.path.join(BASE, "traces", name, "features.csv")
    save(row, out)
    print(f"\n[+] Saved evidence: {out}\n")

    df = pd.DataFrame([row])
    if pipeline == "authors":
        from authors import predict_df
        prob = predict_df(df).iloc[0]
        results = [{"model": m, "pred": int(p >= 0.5), "label": "MALICIOUS" if p >= 0.5 else "BENIGN", "prob": float(p)}
                   for m, p in prob.items()]
    else:
        models = load_models()
        if not models:
            print("Error: No models found.")
            sys.exit(1)
        results = predict_pkg(df, models)
    show(name, results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg", help="package name or tar.gz file")
    ap.add_argument("duration", nargs="?", type=int, default=120, help="seconds to monitor (paper: 120)")
    ap.add_argument("--out", help="output CSV evidence path (default: traces/<pkg>/features.csv)")
    ap.add_argument("--skip", action="store_true", help="skip trace step")
    ap.add_argument("--pipeline", choices=["repo", "authors"], default="repo",
                    help="repo = 36 ordinal-encoded features (models/*.pkl); authors = n-gram pipeline of the "
                         "authors' notebook (models/authors/pipeline.pkl, build with: python src/authors.py train)")
    args = ap.parse_args()

    # trace.sh runs from the repo root, so a local archive needs an absolute path
    pkg = os.path.abspath(args.pkg) if os.path.isfile(args.pkg) else args.pkg
    run(pkg, args.duration, args.out, args.skip, args.pipeline)


if __name__ == "__main__":
    main()
