#!/bin/bash
# Unattended run, in the VM only: benign list x RUNS, then the 11 malicious samples x RUNS
# (network on, as the authors), then src/ablation.py on each run. Output files: ${TAG}_*.
#
#   sudo systemd-inhibit --what=sleep:idle --why=dysec bash src/scripts/overnight.sh 2>&1 | tee overnight.log
#
# Before starting: snapshot the clean VM; turn off Shared Folders, Drag&Drop and Copy/Paste.
# Afterwards: pull ${TAG}_out.tar.gz to the host, then revert the snapshot.
set -u
TAG="${TAG:-lap2}"
RUNS="${RUNS:-2}"
# As in QUT-DV25: benign traced with the default Python 3.12, malicious with Python 3.8
PY_BENIGN=python3
PY_MAL=python3.8
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"
[ "$(id -u)" -eq 0 ] || { echo "Must run with sudo"; exit 1; }
user_home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)

MAL="aaiohttp-0.1 capmonster-task-1.0 boogipoper-0.1.0 boogishell6-0.1.0 corlorama-1.0.0
capmostercloudclieent-1.0.0 cilorama-1.0.0 bip-utjls-1.0.0 assyncio-1.0.0 coloramae-1.0.0 asyincio-1.0.0"

# Trace every package of list $1 into ${prefix}_results/features.csv, then re-run (up to 2 times)
# the packages whose probes died; the re-runs go to ${prefix}_rerun{1,2}_*.csv.
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
print("\n".join(d.loc[d.Probe_Died.astype(str) != "none", "Package_Name"]))
PY
        [ -s "${prefix}_bad.txt" ] || break
        echo "=== $prefix rerun $i: $(wc -l < "${prefix}_bad.txt") packages ($(date '+%T'))"
        PYTHON=$py python3 src/batch.py "${prefix}_bad.txt" \
            --out "${prefix}_rerun${i}_results.csv" --features "${prefix}_rerun${i}_features.csv"
    done
}

echo "=== START $(date) | $(uname -r) | $(nproc) CPU | commit $(git log --oneline -1 2>/dev/null)"

# ---------- Phase A: benign ----------
(echo flask; cat data/benign-test.txt) > "${TAG}_benign.txt"
for run in $(seq 1 "$RUNS"); do
    echo "=== benign run $run: $(wc -l < "${TAG}_benign.txt") packages ($(date '+%T'))"
    measure "${TAG}_benign.txt" "${TAG}_r${run}_benign" "$PY_BENIGN"
done
tar -czf "${TAG}_benign_only.tar.gz" ${TAG}_r*_benign*.csv
echo "=== benign done $(date) | sha256 (before any malware ran): $(sha256sum "${TAG}_benign_only.tar.gz" | cut -d' ' -f1)"

# ---------- Safety checks before malware ----------
if command -v vmware-hgfsclient >/dev/null && [ -n "$(vmware-hgfsclient 2>/dev/null)" ]; then
    echo "!!! Shared Folders are enabled: malicious phase SKIPPED"; exit 1
fi
if grep -qs hgfs /proc/mounts; then
    echo "!!! /mnt/hgfs is mounted: malicious phase SKIPPED"; exit 1
fi
rm -f "$user_home/.git-credentials" /root/.git-credentials
sudo -u "${SUDO_USER:-root}" git config --global --unset-all credential.helper 2>/dev/null
git config --global --unset-all credential.helper 2>/dev/null

# ---------- Phase B: malicious ----------
: > "${TAG}_mal.txt"
for f in $MAL; do
    [ -s "$f.tar.gz" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${f%-*}/${f##*-}/$f.tar.gz" \
        || echo "!!! download failed: $f"
    [ -s "$f.tar.gz" ] && echo "$f.tar.gz" >> "${TAG}_mal.txt"
done
n=$(wc -l < "${TAG}_mal.txt")
echo "=== malicious samples present: $n/11"
[ "$n" -eq 11 ] || { echo "!!! missing samples: malicious phase SKIPPED"; exit 1; }
for run in $(seq 1 "$RUNS"); do
    echo "=== malicious run $run ($(date '+%T'))"
    measure "${TAG}_mal.txt" "${TAG}_r${run}_mal" "$PY_MAL"
done

# ---------- Ablation per run ----------
for run in $(seq 1 "$RUNS"); do
    p="${TAG}_r${run}"
    echo "=== ablation run $run"
    python3 src/ablation.py \
        --benign "${p}_benign_features.csv" $(ls ${p}_benign_rerun*_features.csv 2>/dev/null) \
        --benign-results "${p}_benign_results.csv" $(ls ${p}_benign_rerun*_results.csv 2>/dev/null) \
        --malicious "${p}_mal_features.csv" $(ls ${p}_mal_rerun*_features.csv 2>/dev/null) \
        --malicious-results "${p}_mal_results.csv" $(ls ${p}_mal_rerun*_results.csv 2>/dev/null) \
        | tee "${p}_ablation.txt"
    cp results/ablation.csv "${p}_ablation.csv"
done

tar -czf "${TAG}_out.tar.gz" ${TAG}_*.csv ${TAG}_*.txt
chown "${SUDO_USER:-root}" ${TAG}_* 2>/dev/null
echo "=== ALL DONE $(date) | ${TAG}_out.tar.gz sha256 $(sha256sum "${TAG}_out.tar.gz" | cut -d' ' -f1)"
