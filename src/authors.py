"""Authors' ML pipeline, ported from the public QUT-DV25 notebook
"Technical Validation and Benchmarks/QUT-DV25_Step 2 Traditional ML Implementation/
Dynamic Analysis/CombinedTraces/TML CombinedTraces.ipynb" (github.com/tanzirmehedi/QUT-DV25).

What the notebook does (and this file reproduces):
  * all text columns are joined into one string per package and turned into
    word 2-3-gram counts with CountVectorizer(ngram_range=(2, 3));
  * the numeric columns are stacked in front of the n-gram counts;
  * RF and DT use StandardScaler(with_mean=False); SVM, LR, KNN and GB use the unscaled matrix;
  * split 70/15/15, stratified, random_state=42;
  * hyper-parameters as in the notebook (they differ from the paper text, see MODELS).

The notebook fits the vectorizer and scaler on the whole dataset before splitting.
--fit-scope all keeps that behaviour (exact replication); --fit-scope train fits them on
the training part only, which is the leak-free variant.

Usage:
  python src/authors.py train [--split random|group] [--fit-scope all|train] [--svm]
  python src/authors.py predict <features.csv> [more.csv ...]
"""
import argparse, os, sys, time
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import FEATURES
from preprocess import CAT_COLS

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(BASE, "dataset", "QUT-DV25.csv")
OUT = os.path.join(BASE, "models", "authors", "pipeline.pkl")
NUM_COLS = [c for c in FEATURES if c not in CAT_COLS]   # 17 numeric, dataset order
TXT_COLS = [c for c in FEATURES if c in CAT_COLS]       # 19 text, dataset order

# name: (factory, uses scaled matrix) - values copied from the notebook cells
MODELS = {
    "Random-Forest": (lambda: RandomForestClassifier(n_estimators=10, max_depth=10, random_state=42), True),
    "Decision-Tree": (lambda: DecisionTreeClassifier(max_depth=2, min_samples_split=20, random_state=42), True),
    "Gradient-Boosting": (lambda: GradientBoostingClassifier(n_estimators=10, max_depth=2, learning_rate=0.01, random_state=42), False),
    "Logistic-Regression": (lambda: LogisticRegression(random_state=42, max_iter=2500), False),
    "KNN": (lambda: KNeighborsClassifier(n_neighbors=5), False),
    "SVM": (lambda: SVC(kernel="linear", probability=True, random_state=42), False),
}


def text(df):
    return df[TXT_COLS].fillna("").astype(str).agg(" ".join, axis=1)


def numeric(df):
    return csr_matrix(df[NUM_COLS].apply(pd.to_numeric, errors="coerce").fillna(0).astype(float).values)


def fit_transformers(df):
    vec = CountVectorizer(ngram_range=(2, 3)).fit(text(df))
    scaler = StandardScaler(with_mean=False).fit(hstack([numeric(df), vec.transform(text(df))]))
    return vec, scaler


def matrices(df, vec, scaler):
    X = hstack([numeric(df), vec.transform(text(df))]).tocsr()
    return X, scaler.transform(X)


def metrics(y, p):
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[0, 1]).ravel()
    return {"Accuracy": accuracy_score(y, p), "Precision": precision_score(y, p, zero_division=0),
            "Recall": recall_score(y, p), "F1": f1_score(y, p), "FPR": fp / (fp + tn), "FNR": fn / (fn + tp)}


def split(data, how):
    if how == "random":
        tr, tmp = train_test_split(data, test_size=0.3, random_state=42, stratify=data["Level"])
        va, te = train_test_split(tmp, test_size=0.5, random_state=42, stratify=tmp["Level"])
        return tr, va, te
    names = {p: pd.read_csv(os.path.join(BASE, "dataset", f"{p}.csv"), usecols=["Package_Name"]).Package_Name
             for p in ("train", "val", "test")}
    return tuple(data[data.Package_Name.isin(set(names[p]))] for p in ("train", "val", "test"))


def train(args):
    data = pd.read_csv(DATASET)
    tr, va, te = split(data, args.split)
    vec, scaler = fit_transformers(data if args.fit_scope == "all" else tr)
    print(f"split={args.split} fit-scope={args.fit_scope} train/val/test={len(tr)}/{len(va)}/{len(te)} "
          f"input columns={len(NUM_COLS) + len(vec.vocabulary_)}")
    sets = {n: (*matrices(d, vec, scaler), d["Level"].values) for n, d in (("train", tr), ("val", va), ("test", te))}
    fitted, rows = {}, []
    for name, (make, scaled) in MODELS.items():
        if name == "SVM" and not args.svm:
            continue
        X, Xs, y = sets["train"]
        t = time.time()
        model = make().fit(Xs if scaled else X, y)
        fitted[name] = (model, scaled)
        for part in ("val", "test"):
            X, Xs, y = sets[part]
            rows.append({"Model": name, "Split": part, **metrics(y, model.predict(Xs if scaled else X)),
                         "Train_s": round(time.time() - t, 2)})
    res = pd.DataFrame(rows)
    print(res.round(4).to_string(index=False))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    joblib.dump({"vectorizer": vec, "scaler": scaler, "models": fitted, "split": args.split,
                 "fit_scope": args.fit_scope}, OUT)
    res.to_csv(os.path.join(os.path.dirname(OUT), "results.csv"), index=False)
    print(f"[+] Saved {OUT}")


def load():
    if not os.path.exists(OUT):
        sys.exit(f"Error: {OUT} not found, run: python src/authors.py train")
    return joblib.load(OUT)


def predict_df(df, pipe=None):
    pipe = pipe or load()
    X, Xs = matrices(df, pipe["vectorizer"], pipe["scaler"])
    return pd.DataFrame({name: model.predict_proba(Xs if scaled else X)[:, 1]
                         for name, (model, scaled) in pipe["models"].items()}, index=df.index)


def predict(args):
    pipe = load()
    for path in args.csv:
        df = pd.read_csv(path)
        prob = predict_df(df, pipe)
        prob.insert(0, "Package_Name", df.get("Package_Name", pd.Series(range(len(df)))).values)
        print(prob.round(4).to_string(index=False))
        rf = prob["Random-Forest"]
        print(f"[{os.path.basename(path)}] Random-Forest >= 0.5: {(rf >= 0.5).sum()}/{len(rf)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--split", choices=["random", "group"], default="random",
                   help="random = notebook split (default); group = repo split by package family")
    t.add_argument("--fit-scope", choices=["all", "train"], default="all",
                   help="all = notebook behaviour (default); train = no leakage into val/test")
    t.add_argument("--svm", action="store_true", help="also train linear SVC (hours on CPU)")
    p = sub.add_parser("predict")
    p.add_argument("csv", nargs="+")
    args = ap.parse_args()
    train(args) if args.cmd == "train" else predict(args)


if __name__ == "__main__":
    main()
