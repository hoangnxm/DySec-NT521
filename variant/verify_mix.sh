#!/bin/bash
# Lap E: lap D (110 benign) and lap C (160 malicious) interleaved in one run, order in data/mix-lapE.txt.
# VM ONLY, revert after. Rules: CHAY_KIEM_CHUNG.md. Benign with python3 (as lap D), malicious with python3.8 (as lap C).
#   sudo systemd-inhibit --what=sleep:idle --why=dysec bash variant/verify_mix.sh 2>&1 | tee -a lape.log
# Resumable: run again after a stop, packages already measured are skipped.
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

for f in $(cat data/malicious-lapC.txt); do
    [ -s "$f.tar.gz" ] || wget -q "https://raw.githubusercontent.com/lxyeternal/pypi_malregistry/main/${f%-*}/${f##*-}/$f.tar.gz" || echo "!!! download failed: $f"
done
echo "=== malicious samples present: $(for f in $(cat data/malicious-lapC.txt); do [ -s "$f.tar.gz" ] && echo; done | wc -l)/$(wc -l < data/malicious-lapC.txt)"

# run_list <file with "B name"/"M name" lines> <suffix>: one package at a time, in file order
run_list() {
    local n=0 total kind name pkg py out
    total=$(wc -l < "$1")
    while read -r kind name; do
        name=${name%%[[:space:]]}; n=$((n + 1))
        if [ "$kind" = B ]; then pkg=$name; py=python3; out=lape_ben$2
        else pkg=$name.tar.gz; py=python3.8; out=lape_mal$2; [ -s "$pkg" ] || continue; fi
        grep -qs "^$pkg," "${out}_results.csv" && continue
        echo "--- [$n/$total] $kind $pkg ($(date '+%T'))"
        echo "$pkg" > lape_one.txt
        PYTHON=$py python3 src/batch.py lape_one.txt --out "${out}_results.csv" --features "${out}_features.csv" < /dev/null | grep -v '^\[1/1\]'
    done < "$1"
}

run_list data/mix-lapE.txt ""
for i in 1 2; do
    python3 - > lape_bad.txt <<'PY'
import glob, os
import pandas as pd
out = []
for kind, pre in (("B", "lape_ben"), ("M", "lape_mal")):
    fs = [f for f in [pre + "_results.csv"] + sorted(glob.glob(pre + "_rerun*_results.csv")) if os.path.exists(f)]
    if not fs:
        continue
    d = pd.concat([pd.read_csv(f) for f in fs]).drop_duplicates("Package_Name", keep="last")
    bad = set(d.loc[(d.Probe_Died.astype(str) != "none") | (pd.to_numeric(d.Attach_Delay, errors="coerce") > 10), "Package_Name"])
    out += [(kind, p) for p in bad]
bad = {(k, p[:-7] if k == "M" else p) for k, p in out}
for l in open("data/mix-lapE.txt"):
    k, p = l.split()
    if (k, p) in bad:
        print(k, p)
PY
    [ -s lape_bad.txt ] || break
    echo "=== rerun $i: $(wc -l < lape_bad.txt) packages ($(date '+%T'))"
    run_list lape_bad.txt "_rerun$i"
done

echo "=================== BENIGN (as lap D)"
python3 variant/score_benign.py --features lape_ben_features.csv $(ls lape_ben_rerun*_features.csv 2>/dev/null) \
    --results lape_ben_results.csv $(ls lape_ben_rerun*_results.csv 2>/dev/null) --out lape_ben_scores.csv | tee lape_ben_summary.txt
echo "=================== MALICIOUS (as lap C)"
python3 variant/score_mal.py --features lape_mal_features.csv $(ls lape_mal_rerun*_features.csv 2>/dev/null) \
    --results lape_mal_results.csv $(ls lape_mal_rerun*_results.csv 2>/dev/null) --out lape_mal_scores.csv | tee lape_mal_summary.txt
tar -czf lape_out.tar.gz lape_*.csv lape_*.txt data/mix-lapE.txt lape.log 2>/dev/null
chown "${SUDO_USER:-root}" lape_* 2>/dev/null
echo "=== ALL DONE $(date) | lape_out.tar.gz sha256 $(sha256sum lape_out.tar.gz | cut -d' ' -f1)"
