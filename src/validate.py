import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import FEATURES, extract, packages

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_PROCESSED = os.path.join(BASE, "dataset", "QUT-DV25-Processed")
DIR_RAW = os.path.join(BASE, "dataset", "QUT-DV25-Raw")

GROUPS = {
    "Opensnoop": FEATURES[0:7],
    "TCP": FEATURES[7:12],
    "Filetop": FEATURES[12:17],
    "Install": FEATURES[17:20],
    "SysCall": FEATURES[20:26],
    "Pattern": FEATURES[26:36],
}

csv.field_size_limit(10 ** 9)


def load_truth():
    truth = {}
    for name in GROUPS:
        path = os.path.join(DIR_PROCESSED, f"QUT-DV25-{name}-Traces", f"QUT-DV25-{name}-Traces.csv")
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                truth.setdefault(row["Package_Name"], {}).update(row)
    return truth


def main():
    truth = load_truth()
    per_col = {c: [0, 0] for c in FEATURES}
    for cls in ("Benign", "Malicious"):
        root = os.path.join(DIR_RAW, f"QUT-DV25-{cls}")
        for pkg in packages(root, "qut"):
            if pkg not in truth:
                continue
            mine, ref = extract(root, pkg, "qut"), truth[pkg]
            bad = [c for c in FEATURES if str(mine[c]) != ref.get(c)]
            for c in FEATURES:
                per_col[c][0] += c not in bad
                per_col[c][1] += 1
            print(f"[{cls:9s}] {pkg:28s} {36 - len(bad):2d}/36" + (f"  diff: {', '.join(bad)}" if bad else ""))

    ok = sum(v[0] for v in per_col.values())
    n = sum(v[1] for v in per_col.values())
    if n == 0:
        print("Error: No raw traces found in dataset/QUT-DV25-Raw/")
        return
    print("\nPer trace group:")
    for g, cols in GROUPS.items():
        g_ok = sum(per_col[c][0] for c in cols)
        g_n = sum(per_col[c][1] for c in cols)
        print(f"  {g:10s} {g_ok:5d}/{g_n:<5d} ({100 * g_ok / g_n:5.1f}%)")
    print(f"\nTotal: {ok}/{n} exact matches ({100 * ok / n:.1f}%)")


if __name__ == "__main__":
    main()
