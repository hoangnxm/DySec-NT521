#!/bin/bash
set -u

if [ -z "${1:-}" ]; then
    echo "Usage: sudo [OFFLINE=1] [PYTHON=python3.8] ./trace.sh <package|file.tar.gz> [seconds=120]"
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Must run with sudo"
    exit 1
fi

spec="$1"
duration="${2:-120}"
py="${PYTHON:-python3}"
# A local archive is installed from its path but stored under its base name
if [ -f "$spec" ] || { [[ "$spec" == */* ]] && [ -e "$spec" ]; }; then
    spec="$(cd "$(dirname "$spec")" && pwd)/$(basename "$spec")"
fi
pkg="$(basename "${spec%/}")"
base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"

out="traces/${pkg}"
venv="env/${pkg}"
rm -rf "$out"
mkdir -p "$out" env

opts=""
if [ "${OFFLINE:-0}" = 1 ]; then
    opts="--no-index --find-links $(pwd)/wheelhouse/${py}"
    [ -d "wheelhouse/${py}" ] || { echo "Missing wheelhouse/${py} - download before offline run"; exit 1; }
fi

rm -rf "$venv"
$py -m venv "$venv" || { echo "Failed to create venv with $py"; exit 1; }
"$venv/bin/pip" install $opts --upgrade pip setuptools wheel >/dev/null 2>&1

export PYTHONUNBUFFERED=1
mkdir -p "$out/errors"
filetop-bpfcc 5 > "$out/${pkg}_filetop_trace.txt" 2>"$out/errors/filetop_trace.err" & fpid=$!
opensnoop-bpfcc -d 10 > "$out/${pkg}_opensnoop_trace.txt" 2>"$out/errors/opensnoop_trace.err" & opid=$!
tcpstates-bpfcc > "$out/${pkg}_tcp_trace.txt" 2>"$out/errors/tcp_trace.err" & tpid=$!
bash "$base/src/scripts/monitor.sh" "$pkg" > "$out/monitor.log" 2>&1 & mpid=$!
sleep 5

start=$(date +%s)
echo "Installing $pkg ..."
"$venv/bin/pip" install $opts "$spec" --no-cache-dir 2>&1 | tee "$out/${pkg}_install_log.txt"
status=${PIPESTATUS[0]}

remain=$(( duration - ($(date +%s) - start) ))
if [ "$remain" -gt 0 ]; then
    sleep "$remain"
fi

warn=""
for pair in "filetop:$fpid" "tcpstates:$tpid"; do
    kill -0 "${pair#*:}" 2>/dev/null || warn="$warn ${pair%%:*}"
done
kill $fpid $opid $tpid $mpid 2>/dev/null
pkill -x strace 2>/dev/null
sleep 1

[ "$status" -eq 0 ] && result=Success || result=Failed
echo "$pkg,$result,$(date '+%F %T'),probe_died:${warn:- none}" >> traces/status.csv
echo "[+] Done - $result. eBPF trace: $out | system call trace: outputs/$pkg"
if [ -n "$warn" ]; then
    echo "[!] Probes died early:$warn -> check $out/errors/*.err and re-run"
fi