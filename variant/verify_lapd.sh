#!/bin/bash
# Lap D: 110 NEW benign packages (data/benign-lapD.txt), scored by the three models while measuring.
# No malware. Run on a VM just reverted. Rules: variant/PROTOCOL-D.md
#   sudo systemd-inhibit --what=sleep:idle --why=dysec bash variant/verify_lapd.sh 2>&1 | tee -a lapd.log
# Resumable: run again after a stop, packages already in lapd_results.csv are skipped.
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
echo "=== START $(date) | $(nproc) CPU | commit $(git log --oneline -1 2>/dev/null)"
python3 variant/train_variant.py || exit 1
sha256sum variant/*.pkl models/Random-Forest.pkl

PYTHON=python3 python3 src/batch.py data/benign-lapD.txt --out lapd_results.csv --features lapd_features.csv
for i in 1 2; do
    python3 - > lapd_bad.txt <<'PY'
import glob
import pandas as pd
fs = ["lapd_results.csv"] + sorted(glob.glob("lapd_rerun*_results.csv"))
d = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("Package_Name", keep="last")
bad = (d.Probe_Died.astype(str) != "none") | (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10)
print("\n".join(d.loc[bad, "Package_Name"]))
PY
    [ -s lapd_bad.txt ] || break
    echo "=== rerun $i: $(wc -l < lapd_bad.txt) packages ($(date '+%T'))"
    PYTHON=python3 python3 src/batch.py lapd_bad.txt --out "lapd_rerun${i}_results.csv" --features "lapd_rerun${i}_features.csv"
done

python3 variant/score_benign.py --features lapd_features.csv $(ls lapd_rerun*_features.csv 2>/dev/null) \
    --results lapd_results.csv $(ls lapd_rerun*_results.csv 2>/dev/null) --out lapd_scores.csv | tee lapd_summary.txt
tar -czf lapd_out.tar.gz lapd_*.csv lapd_*.txt lapd.log 2>/dev/null
chown "${SUDO_USER:-root}" lapd_* 2>/dev/null
echo "=== ALL DONE $(date) | lapd_out.tar.gz sha256 $(sha256sum lapd_out.tar.gz | cut -d' ' -f1)"
