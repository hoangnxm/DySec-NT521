#!/bin/bash
# Lần đo B: gói lành MỚI (data/benign-fresh.txt) chấm bằng cả ba model ngay lúc đo. Chạy trên VM vừa revert.
#   sudo systemd-inhibit --what=sleep:idle --why=dysec bash variant/verify_fresh.sh 2>&1 | tee -a verify_fresh.log
# Không chạy gói độc. Gói độc: lần A (variant/verify.sh, 40 gói).
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
echo "=== START $(date) | $(nproc) CPU | commit $(git log --oneline -1 2>/dev/null)"
python3 variant/train_variant.py || exit 1
sha256sum variant/*.pkl models/Random-Forest.pkl
PYTHON=python3 python3 src/batch.py data/benign-fresh.txt --out fresh_results.csv --features fresh_features.csv
python3 - <<'PY'
import pandas as pd
d = pd.read_csv("fresh_results.csv")
bad = d[(d.Probe_Died.astype(str) != "none") | (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10)].Package_Name
open("fresh_bad.txt", "w").write("\n".join(bad))
PY
if [ -s fresh_bad.txt ]; then
    echo "=== rerun $(wc -l < fresh_bad.txt) packages"
    PYTHON=python3 python3 src/batch.py fresh_bad.txt --out fresh_rerun_results.csv --features fresh_rerun_features.csv
fi
tar -czf fresh_out.tar.gz fresh_*.csv fresh_*.txt 2>/dev/null
chown "${SUDO_USER:-root}" fresh_* 2>/dev/null
echo "=== ALL DONE $(date) | fresh_out.tar.gz sha256 $(sha256sum fresh_out.tar.gz | cut -d' ' -f1)"
