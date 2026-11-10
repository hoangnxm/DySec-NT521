#!/bin/bash
# Lap C: recall on 160 new malicious packages (Python 3.8). VM ONLY, revert after. Rules: variant/PROTOCOL-C.md
#   Before: Shared Folders / Drag&Drop / Copy&Paste OFF, snapshot taken. Network ON (NAT, as the authors).
#   sudo systemd-inhibit --what=sleep:idle --why=dysec bash variant/verify_mal.sh 2>&1 | tee -a lapc.log
# Resumable: run again after a stop, packages already in lapc_results.csv are skipped.
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
user_home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
echo "=== START $(date) | $(nproc) CPU | commit $(git log --oneline -1 2>/dev/null)"
python3 variant/train_variant.py || exit 1
sha256sum variant/*.pkl models/Random-Forest.pkl

if command -v vmware-hgfsclient >/dev/null && [ -n "$(vmware-hgfsclient 2>/dev/null)" ]; then echo "!!! Shared Folders on: stop"; exit 1; fi
if grep -qs hgfs /proc/mounts; then echo "!!! hgfs mounted: stop"; exit 1; fi
rm -f "$user_home/.git-credentials" /root/.git-credentials
sudo -u "${SUDO_USER:-root}" git config --global --unset-all credential.helper 2>/dev/null
git config --global --unset-all credential.helper 2>/dev/null

: > lapc.txt
for f in $(cat data/malicious-lapC.txt); do
    [ -s "$f.tar.gz" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${f%-*}/${f##*-}/$f.tar.gz" || echo "!!! download failed: $f"
    [ -s "$f.tar.gz" ] && echo "$f.tar.gz" >> lapc.txt
done
echo "=== malicious samples present: $(wc -l < lapc.txt)/$(wc -l < data/malicious-lapC.txt)"

PYTHON=python3.8 python3 src/batch.py lapc.txt --out lapc_results.csv --features lapc_features.csv
for i in 1 2; do
    python3 - > lapc_bad.txt <<'PY'
import glob
import pandas as pd
fs = ["lapc_results.csv"] + sorted(glob.glob("lapc_rerun*_results.csv"))
d = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("Package_Name", keep="last")
bad = (d.Probe_Died.astype(str) != "none") | (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10)
print("\n".join(d.loc[bad, "Package_Name"]))
PY
    [ -s lapc_bad.txt ] || break
    echo "=== rerun $i: $(wc -l < lapc_bad.txt) packages ($(date '+%T'))"
    PYTHON=python3.8 python3 src/batch.py lapc_bad.txt --out "lapc_rerun${i}_results.csv" --features "lapc_rerun${i}_features.csv"
done

python3 variant/score_mal.py --features lapc_features.csv $(ls lapc_rerun*_features.csv 2>/dev/null) \
    --results lapc_results.csv $(ls lapc_rerun*_results.csv 2>/dev/null) --out lapc_scores.csv | tee lapc_summary.txt
tar -czf lapc_out.tar.gz lapc_*.csv lapc_*.txt lapc.log 2>/dev/null
chown "${SUDO_USER:-root}" lapc_* 2>/dev/null
echo "=== ALL DONE $(date) | lapc_out.tar.gz sha256 $(sha256sum lapc_out.tar.gz | cut -d' ' -f1)"
