#!/bin/bash
# Check the variant (drop G1+G2) against the authors' RF on fresh traces. VM only, network on (as the authors).
#   sudo systemd-inhibit --what=sleep:idle --why=dysec bash variant/verify.sh 2>&1 | tee -a verify.log
# 1) train the variant  2) benign list (Python 3.12)  3) safety checks  4) 40 new malicious (Python 3.8)  5) score
# Resumable: run the same command again after a stop, packages already in ver_*_results.csv are skipped.
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
user_home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
echo "=== START $(date) | $(nproc) CPU | commit $(git log --oneline -1 2>/dev/null)"

python3 variant/train_variant.py || exit 1

# Trace list $1 into ${2}_results/features.csv, then re-run (up to 2 times) the packages whose probes died
measure() {
    local list=$1 prefix=$2 py=$3 i
    PYTHON=$py python3 src/batch.py "$list" --out "${prefix}_results.csv" --features "${prefix}_features.csv"
    for i in 1 2; do
        python3 - "$prefix" > "${prefix}_bad.txt" <<'PY'
import glob, sys
import pandas as pd
p = sys.argv[1]
fs = [p + "_results.csv"] + sorted(glob.glob(p + "_rerun*_results.csv"))
d = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("Package_Name", keep="last")
bad = (d.Probe_Died.astype(str) != "none") | (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10)
print("\n".join(d.loc[bad, "Package_Name"]))
PY
        [ -s "${prefix}_bad.txt" ] || break
        echo "=== $prefix rerun $i: $(wc -l < "${prefix}_bad.txt") packages ($(date '+%T'))"
        PYTHON=$py python3 src/batch.py "${prefix}_bad.txt" \
            --out "${prefix}_rerun${i}_results.csv" --features "${prefix}_rerun${i}_features.csv"
    done
}

# ---------- benign (before any malware) ----------
(echo flask; cat data/benign-test.txt) | grep -vxFf data/benign-heavy.txt > ver_benign.txt
echo "=== benign: $(wc -l < ver_benign.txt) packages ($(date '+%T'))"
measure ver_benign.txt ver_benign python3
tar -czf ver_benign_only.tar.gz ver_benign*.csv
echo "=== benign done $(date) | sha256 $(sha256sum ver_benign_only.tar.gz | cut -d' ' -f1)"

# ---------- safety checks ----------
if command -v vmware-hgfsclient >/dev/null && [ -n "$(vmware-hgfsclient 2>/dev/null)" ]; then echo "!!! Shared Folders on: stop"; exit 1; fi
if grep -qs hgfs /proc/mounts; then echo "!!! hgfs mounted: stop"; exit 1; fi
rm -f "$user_home/.git-credentials" /root/.git-credentials
sudo -u "${SUDO_USER:-root}" git config --global --unset-all credential.helper 2>/dev/null
git config --global --unset-all credential.helper 2>/dev/null

# ---------- 40 new malicious (authors' test split, not used to choose the variant) ----------
: > ver_mal.txt
for f in $(cat data/malicious-more.txt); do
    [ -s "$f.tar.gz" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${f%-*}/${f##*-}/$f.tar.gz" || echo "!!! download failed: $f"
    [ -s "$f.tar.gz" ] && echo "$f.tar.gz" >> ver_mal.txt
done
echo "=== malicious samples present: $(wc -l < ver_mal.txt)/$(wc -l < data/malicious-more.txt)"
measure ver_mal.txt ver_mal python3.8

# ---------- score ----------
python3 variant/score.py \
    --benign ver_benign_features.csv $(ls ver_benign_rerun*_features.csv 2>/dev/null) \
    --benign-results ver_benign_results.csv $(ls ver_benign_rerun*_results.csv 2>/dev/null) \
    --malicious ver_mal_features.csv $(ls ver_mal_rerun*_features.csv 2>/dev/null) \
    --malicious-results ver_mal_results.csv $(ls ver_mal_rerun*_results.csv 2>/dev/null) \
    --out ver_scores.csv | tee ver_summary.txt
tar -czf ver_out.tar.gz ver_*.csv ver_*.txt verify.log 2>/dev/null
chown "${SUDO_USER:-root}" ver_* 2>/dev/null
echo "=== ALL DONE $(date) | ver_out.tar.gz sha256 $(sha256sum ver_out.tar.gz | cut -d' ' -f1)"
