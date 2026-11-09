"""Variant models: the repo's Random Forest retrained from scratch on dataset/train.csv WITHOUT
G1 (Filetop process names) + G2 (system call counts) -> 25 cols, and also without G3 (dependencies) -> 22 cols.

Same encoder (src/preprocess.py), same RF settings as src/train.py (100 trees, max_depth 8, seed 50),
same threshold 0.5. Only the column set changes. The authors' model in models/ is not touched.

  python3 variant/train_variant.py   -> variant/rf_drop_g1g2.pkl, variant/rf_drop_g1g2g3.pkl, prints dataset/test.csv metrics
"""
import os, sys, joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BASE, "src"))
from extract import FEATURES
from preprocess import transform

DROP = {
    "G1": ["Read_Processes", "Write_Processes", "Read_Data_Transfer_Processes",
           "Write_Data_Transfer_Processes", "File_Access_Processes"],
    "G2": ["File_Operations", "Network_Operations", "Process_Management_Operations",
           "IO_Operations", "Time_Operations", "Security_Operations"],
    "G3": ["Total_Dependencies", "Direct_Dependencies", "Indirect_Dependencies"],
}
VARIANTS = {"drop_g1g2": ["G1", "G2"], "drop_g1g2g3": ["G1", "G2", "G3"]}


def cols(name):
    gone = sum((DROP[g] for g in VARIANTS[name]), [])
    return [c for c in FEATURES if c not in gone]


def load(name):
    df = pd.read_csv(os.path.join(BASE, "dataset", name))
    return transform(df), df["Level"].values


def metrics(model, X, y, cols):
    tn, fp, fn, tp = confusion_matrix(y, model.predict(X[cols]), labels=[0, 1]).ravel()
    return (tp + tn) / len(y), tp / (tp + fn), fp / (fp + tn)


def main():
    Xtr, ytr = load("train.csv")
    Xte, yte = load("test.csv")
    for name in VARIANTS:
        c = cols(name)
        rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=50, n_jobs=-1)
        rf.fit(Xtr[c], ytr)
        path = os.path.join(HERE, f"rf_{name}.pkl")
        joblib.dump({"model": rf, "cols": c}, path)
        acc, rec, fpr = metrics(rf, Xte, yte, c)
        print(f"[+] {name} ({len(c)} cols) saved {path}")
        print(f"    dataset/test.csv: acc {acc:.2%} recall {rec:.2%} FPR {fpr:.2%}")
    orig = joblib.load(os.path.join(BASE, "models", "Random-Forest.pkl"))
    acc, rec, fpr = metrics(orig, Xte, yte, FEATURES)
    print(f"    authors' RF (36 cols) on the same test: acc {acc:.2%} recall {rec:.2%} FPR {fpr:.2%}")


if __name__ == "__main__":
    main()
