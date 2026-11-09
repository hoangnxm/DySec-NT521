import argparse, csv, os, shutil, subprocess, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import extract, FEATURES
from predict import load_models, predict_pkg

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(BASE, "src", "scripts", "trace.sh")


def status(pkg):
    path = os.path.join(BASE, "traces", "status.csv")
    last = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith(pkg + ","):
                    last = line.strip().split(",")
    if not last or len(last) < 4:
        return "Failed", "unknown"
    return last[1], last[3].replace("probe_died:", "").strip()


def timing(pkg):
    """Attach delay of strace on the main pip process and pip's install time (seconds), or ''."""
    d = os.path.join(BASE, "traces", os.path.basename(pkg))
    delay = secs = ""
    try:
        rows = [l.split() for l in open(os.path.join(d, "attach_delay.txt")) if len(l.split()) == 3]
        main = [r for r in rows if r[1] in ("pip", "pip3")] or rows
        delay = main[0][2] if main else ""
    except OSError:
        pass
    try:
        secs = open(os.path.join(d, "install_seconds.txt")).read().strip()
    except OSError:
        pass
    return delay, secs


def done(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {r["Package_Name"] for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser(description="Trace, extract and predict a list of packages (resumable)")
    ap.add_argument("list", help="text file, one package (or .tar.gz in repo root) per line")
    ap.add_argument("--duration", type=int, default=120)
    ap.add_argument("--out", default="batch_results.csv")
    ap.add_argument("--features", default="batch_features.csv")
    ap.add_argument("--no-trace", action="store_true", help="reuse existing traces/ and outputs/")
    args = ap.parse_args()

    if not args.no_trace and os.name != "nt" and os.geteuid() != 0:
        print("Error: Must run with sudo to capture eBPF traces.")
        sys.exit(1)

    pkgs = [l.strip() for l in open(args.list, encoding="utf-8") if l.strip()]
    models = load_models()
    skip = done(args.out)
    new_out, new_feat = not os.path.exists(args.out), not os.path.exists(args.features)
    log = open(os.path.join(BASE, "batch.log"), "a")

    with open(args.out, "a", newline="", encoding="utf-8") as fo, \
         open(args.features, "a", newline="", encoding="utf-8") as ff:
        cols = ["Package_Name", "Status", "Probe_Died", "Attach_Delay", "Install_Seconds"] + list(models)
        if not new_out:                      # resuming an older CSV: keep its columns
            with open(args.out, encoding="utf-8") as f:
                cols = next(csv.reader(f), cols)
        wo = csv.DictWriter(fo, fieldnames=cols, extrasaction="ignore")
        wf = csv.DictWriter(ff, fieldnames=["Package_Name"] + FEATURES)
        if new_out:
            wo.writeheader()
        if new_feat:
            wf.writeheader()

        for i, pkg in enumerate(pkgs, 1):
            if pkg in skip:
                continue
            print(f"[{i}/{len(pkgs)}] {pkg}", flush=True)
            if not args.no_trace:
                try:
                    subprocess.run(["bash", SCRIPT, pkg, str(args.duration)], cwd=BASE,
                                   stdout=log, stderr=log, timeout=args.duration + 900)
                except subprocess.TimeoutExpired:
                    # trace.sh was killed before its own cleanup: stop everything it started
                    subprocess.run(["pkill", "-KILL", "-f", "[s]rc/scripts/monitor.sh"])
                    subprocess.run(["pkill", "-KILL", "-f", "[f]iletop-bpfcc|[o]pensnoop-bpfcc|[t]cpstates-bpfcc"])
                    subprocess.run(["pkill", "-KILL", "-x", "strace"])
                    # the orphan pip of the killed trace.sh would be attached by the next package's monitor
                    subprocess.run(["pkill", "-KILL", "-f", "[e]nv/.*/bin/(pip|python)"])
                    print("    timeout: trace.sh killed", flush=True)
                shutil.rmtree(os.path.join(BASE, "env", os.path.basename(pkg)), ignore_errors=True)
                st, died = status(pkg)
            else:
                st, died = "Success", "none"

            delay, secs = timing(pkg)
            row = {"Package_Name": pkg, "Status": st, "Probe_Died": died,
                   "Attach_Delay": delay, "Install_Seconds": secs}
            if os.path.isdir(os.path.join(BASE, "traces", pkg)):
                feats = extract(BASE, pkg)
                wf.writerow({k: feats.get(k, "") for k in ["Package_Name"] + FEATURES})
                ff.flush()
                for r in predict_pkg(pd.DataFrame([feats]), models):
                    row[r["model"]] = round(r["prob"], 4) if r["prob"] is not None else ""
            wo.writerow(row)
            fo.flush()
            print(f"    {st} probe_died={died} delay={delay or '-'}s install={secs or '-'}s RF={row.get('Random-Forest', '-')}", flush=True)


if __name__ == "__main__":
    main()
