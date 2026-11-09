#!/bin/bash
# 40 more malicious packages (authors' test split, one per name family) + ablation on all malicious data. VM only.
#   N=40 sudo -E bash src/scripts/mal_more.sh 2>&1 | tee mal_more.log
set -u
N="${N:-40}"
PY_MAL=python3.8
cd "$(cd "$(dirname "$0")/../.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
user_home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
if command -v vmware-hgfsclient >/dev/null && [ -n "$(vmware-hgfsclient 2>/dev/null)" ]; then echo "!!! Shared Folders on: stop"; exit 1; fi
if grep -qs hgfs /proc/mounts; then echo "!!! hgfs mounted: stop"; exit 1; fi
rm -f "$user_home/.git-credentials" /root/.git-credentials
sudo -u "${SUDO_USER:-root}" git config --global --unset-all credential.helper 2>/dev/null
git config --global --unset-all credential.helper 2>/dev/null
: > lap2_more.txt
for f in $(head -n "$N" data/malicious-more.txt); do
    [ -s "$f.tar.gz" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${f%-*}/${f##*-}/$f.tar.gz" || echo "!!! download failed: $f"
    [ -s "$f.tar.gz" ] && echo "$f.tar.gz" >> lap2_more.txt
done
echo "=== samples present: $(wc -l < lap2_more.txt)/$N"
PYTHON=$PY_MAL python3 src/batch.py lap2_more.txt --out lap2_r1_more_results.csv --features lap2_r1_more_features.csv
python3 src/ablation.py \
    --benign lap2_r1_benign_features.csv $(ls lap2_r1_benign_rerun*_features.csv 2>/dev/null) \
    --benign-results lap2_r1_benign_results.csv $(ls lap2_r1_benign_rerun*_results.csv 2>/dev/null) \
    --malicious lap2_r1_mal_features.csv lap2_r1_more_features.csv \
    --malicious-results lap2_r1_mal_results.csv lap2_r1_more_results.csv | tee lap2_r1_ablation_more.txt
echo "=== DONE $(date)"; cat lap2_r1_more_results.csv
