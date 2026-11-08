"""Feature-group ablation: remove one group (or a combination) at a time, retrain RF, measure.

Each configuration drops a set of feature groups, retrains the repo's Random Forest
(100 trees, max_depth 8, same encoder as src/preprocess.py) on dataset/train.csv with
several seeds, and reports:
  * dataset/test.csv: accuracy, recall, FPR
  * optional field data traced in the VM: FPR on benign packages, recall on malicious ones

Field CSVs are the --features files written by src/batch.py. Pass the matching --out
files with --*-results so that runs with probe_died != none are left out (last row per
package wins, so re-runs replace failed runs).

Usage:
  python src/ablation.py
  python src/ablation.py --benign poll_benign_features.csv rerun8_features.csv \
      --benign-results poll_benign_results.csv rerun8_results.csv \
      --malicious poll_mal_features.csv --malicious-results poll_mal_results.csv
"""
import argparse, itertools, os, sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import FEATURES
from preprocess import transform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "results", "ablation.csv")

# 36 features split by trace source; TCP is split into State_Transition and IP/port
GROUPS = {
    "G1 process names (Filetop)": ["Read_Processes", "Write_Processes", "Read_Data_Transfer_Processes",
                                   "Write_Data_Transfer_Processes", "File_Access_Processes"],
    "G2 syscall counts (SystemCall)": ["File_Operations", "Network_Operations", "Process_Management_Operations",
                                       "IO_Operations", "Time_Operations", "Security_Operations"],
    "G3 dependencies (Install)": ["Total_Dependencies", "Direct_Dependencies", "Indirect_Dependencies"],
    "G4 State_Transition (TCP)": ["State_Transition"],
    "G5 IP/port (TCP)": ["Local_IP_Address_Access", "Remote_IP_Address_Access", "Local_Port_Access",
                         "Remote_Port_Access"],
    "G6 directories (Opensnoop)": ["Root_DIR_Installation", "Temporary_DIR_Installation", "Home_DIR_Installation",
                                   "User_Access", "Sys_Access", "Etc_DIR_Installation", "Other_DIR_Installation"],
    "G7 patterns (Pattern)": [f"Pattern_{i}" for i in range(1, 11)],
}
assert sorted(sum(GROUPS.values(), [])) == sorted(FEATURES)


def configs():
    yield "baseline (36)", []
    for g in GROUPS:                                    # one group at a time
        yield f"drop {g[:2]}", [g]
    suspects = list(GROUPS)[:3]                         # G1, G2, G3
    for k in (2, 3):
        for combo in itertools.combinations(suspects, k):
            yield "drop " + "+".join(c[:2] for c in combo), list(combo)


def load_xy(path):
    df = pd.read_csv(path)
    return transform(df), df["Level"].values


def load_field(feats, results):
    if not feats:
        return None
    df = pd.concat([pd.read_csv(f) for f in feats]).drop_duplicates("Package_Name", keep="last")
    if results:
        r = pd.concat([pd.read_csv(f) for f in results]).drop_duplicates("Package_Name", keep="last")
        bad = set(r.loc[r["Probe_Died"].astype(str) != "none", "Package_Name"])
        df = df[~df["Package_Name"].isin(bad)]
    return transform(df).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benign", nargs="*", default=[])
    ap.add_argument("--benign-results", nargs="*", default=[])
    ap.add_argument("--malicious", nargs="*", default=[])
    ap.add_argument("--malicious-results", nargs="*", default=[])
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()

    Xtr, ytr = load_xy(os.path.join(BASE, "dataset", "train.csv"))
    Xte, yte = load_xy(os.path.join(BASE, "dataset", "test.csv"))
    ben = load_field(args.benign, args.benign_results)
    mal = load_field(args.malicious, args.malicious_results)
    print(f"train {len(Xtr)} | test {len(Xte)} | field benign {0 if ben is None else len(ben)}"
          f" | field malicious {0 if mal is None else len(mal)} | seeds {args.seeds}")

    rows = []
    for name, drop in configs():
        cols = [c for c in FEATURES if c not in sum((GROUPS[g] for g in drop), [])]
        res = []
        for seed in range(args.seeds):
            rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=seed, n_jobs=-1)
            rf.fit(Xtr[cols], ytr)
            tn, fp, fn, tp = confusion_matrix(yte, rf.predict(Xte[cols]), labels=[0, 1]).ravel()
            r = {"acc": (tp + tn) / len(yte), "recall": tp / (tp + fn), "fpr": fp / (fp + tn)}
            if ben is not None:
                r["field_fp"] = int((rf.predict_proba(ben[cols])[:, 1] >= 0.5).sum())
            if mal is not None:
                r["field_tp"] = int((rf.predict_proba(mal[cols])[:, 1] >= 0.5).sum())
            res.append(r)
        d = pd.DataFrame(res)
        row = {"config": name, "n_features": len(cols),
               "test_acc": d.acc.mean(), "test_acc_std": d.acc.std(),
               "test_recall": d.recall.mean(), "test_fpr": d.fpr.mean(), "test_fpr_std": d.fpr.std()}
        if ben is not None:
            row.update(field_benign_fp=d.field_fp.mean(), field_benign_fp_min=d.field_fp.min(),
                       field_benign_fp_max=d.field_fp.max(), field_benign_n=len(ben),
                       field_fpr=d.field_fp.mean() / len(ben))
        if mal is not None:
            row.update(field_mal_tp=d.field_tp.mean(), field_mal_tp_min=d.field_tp.min(),
                       field_mal_n=len(mal), field_recall=d.field_tp.mean() / len(mal))
        rows.append(row)
        msg = (f"{name:22s} {len(cols):2d} cols | test acc {row['test_acc']:.2%} recall {row['test_recall']:.2%}"
               f" FPR {row['test_fpr']:.2%}")
        if ben is not None:
            msg += f" | field FP {row['field_benign_fp']:.1f}/{len(ben)} ({row['field_fpr']:.1%})"
        if mal is not None:
            msg += f" | field TP {row['field_mal_tp']:.1f}/{len(mal)}"
        print(msg, flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"[+] Saved {OUT}")
    print("Groups:")
    for g, c in GROUPS.items():
        print(f"  {g}: {', '.join(c)}")


if __name__ == "__main__":
    main()
