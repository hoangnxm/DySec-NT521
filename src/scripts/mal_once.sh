#!/bin/bash
# Malicious phase only (1 run) of overnight.sh, then the ablation with lap2_r1 benign data. VM only, network on as the authors.
#   sudo bash src/scripts/mal_once.sh 2>&1 | tee mal_once.log
set -u
TAG="${TAG:-lap2}"
PY_MAL=python3.8
cd "$(cd "$(dirname "$0")/../.." && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
user_home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
MAL="aaiohttp-0.1 capmonster-task-1.0 boogipoper-0.1.0 boogishell6-0.1.0 corlorama-1.0.0
capmostercloudclieent-1.0.0 cilorama-1.0.0 bip-utjls-1.0.0 assyncio-1.0.0 coloramae-1.0.0 asyincio-1.0.0"
if command -v vmware-hgfsclient >/dev/null && [ -n "$(vmware-hgfsclient 2>/dev/null)" ]; then echo "!!! Shared Folders on: stop"; exit 1; fi
if grep -qs hgfs /proc/mounts; then echo "!!! hgfs mounted: stop"; exit 1; fi
rm -f "$user_home/.git-credentials" /root/.git-credentials
sudo -u "${SUDO_USER:-root}" git config --global --unset-all credential.helper 2>/dev/null
git config --global --unset-all credential.helper 2>/dev/null
: > "${TAG}_mal.txt"
for f in $MAL; do
    [ -s "$f.tar.gz" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${f%-*}/${f##*-}/$f.tar.gz" || echo "!!! download failed: $f"
    [ -s "$f.tar.gz" ] && echo "$f.tar.gz" >> "${TAG}_mal.txt"
done
n=$(wc -l < "${TAG}_mal.txt"); echo "=== malicious samples present: $n/11"
[ "$n" -eq 11 ] || { echo "!!! missing samples: stop"; exit 1; }
p="${TAG}_r1"
PYTHON=$PY_MAL python3 src/batch.py "${TAG}_mal.txt" --out "${p}_mal_results.csv" --features "${p}_mal_features.csv"
python3 src/ablation.py \
    --benign "${p}_benign_features.csv" $(ls ${p}_benign_rerun*_features.csv 2>/dev/null) \
    --benign-results "${p}_benign_results.csv" $(ls ${p}_benign_rerun*_results.csv 2>/dev/null) \
    --malicious "${p}_mal_features.csv" --malicious-results "${p}_mal_results.csv" | tee "${p}_ablation_mal.txt"
echo "=== DONE $(date)"; cat "${p}_mal_results.csv"
