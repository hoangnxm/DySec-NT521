#!/bin/bash
# After overnight.sh: re-measure the benign runs spoiled by an orphan pip (attach delay > 10 s or no install time).
#   sudo bash src/scripts/redo_bad.sh
set -u
TAG="${TAG:-lap2}"
cd "$(cd "$(dirname "$0")/../.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
for run in 1 2; do
    p="${TAG}_r${run}_benign"
    python3 - "$p" > "${p}_spoiled.txt" <<'PY'
import glob, sys, pandas as pd
p = sys.argv[1]
fs = [p + "_results.csv"] + sorted(glob.glob(p + "_rerun*_results.csv"))
d = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("Package_Name", keep="last")
bad = d[(pd.to_numeric(d.Attach_Delay, errors="coerce") > 10) | pd.to_numeric(d.Install_Seconds, errors="coerce").isna()]
print("\n".join(bad.Package_Name))
PY
    echo "=== run $run: $(wc -l < ${p}_spoiled.txt) spoiled packages"
    [ -s "${p}_spoiled.txt" ] && PYTHON=python3 python3 src/batch.py "${p}_spoiled.txt" \
        --out "${p}_rerun9_results.csv" --features "${p}_rerun9_features.csv"
done
echo "=== REDO DONE"
