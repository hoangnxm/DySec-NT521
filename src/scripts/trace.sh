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

# Stop leftovers of an earlier run (a stale monitor.sh would grab pip with its own strace
# and leave this run with an empty system call trace). [x] keeps pkill from matching itself.
cleanup_stale() {
    pkill -KILL -f '[s]rc/scripts/monitor.sh' 2>/dev/null
    pkill -KILL -f '[f]iletop-bpfcc|[o]pensnoop-bpfcc|[t]cpstates-bpfcc' 2>/dev/null
    pkill -KILL -x strace 2>/dev/null
    return 0
}
cleanup_stale

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
# Versions seen in QUT-DV25 raw traces: pip 24.3.1, setuptools 75.3.0, wheel 0.43.0 (benign, py3.12) / 0.45.1 (malicious, py3.8)
[ "$py" = python3.8 ] && wheel_ver=0.45.1 || wheel_ver=0.43.0
"$venv/bin/pip" install $opts --upgrade "pip==24.3.1" "setuptools==75.3.0" "wheel==${WHEEL:-$wheel_ver}" >/dev/null 2>&1 \
    || { echo "Failed to prepare venv (pip/setuptools/wheel)"; exit 1; }

export PYTHONUNBUFFERED=1
mkdir -p "$out/errors"
# Same order as the authors' trace.sh (QUT-DV25, Phase iii): strace monitor first, then the 3 eBPF tools, wait 5 s
# STRACE=poll (default, as the authors): monitor.sh looks for python/pip every second and attaches strace.
# STRACE=wrap: pip runs under strace from its first syscall (deterministic; polling misses pip's early network calls).
mode="${STRACE:-poll}"
mpid=""
if [ "$mode" = wrap ]; then
    rm -rf "outputs/$pkg"; mkdir -p "outputs/$pkg"
else
    bash "$base/src/scripts/monitor.sh" "$pkg" > "$out/monitor.log" 2>&1 & mpid=$!
fi
filetop-bpfcc 5 > "$out/${pkg}_filetop_trace.txt" 2>"$out/errors/filetop_trace.err" & fpid=$!
opensnoop-bpfcc -d 10 > "$out/${pkg}_opensnoop_trace.txt" 2>"$out/errors/opensnoop_trace.err" & opid=$!
tcpstates-bpfcc > "$out/${pkg}_tcp_trace.txt" 2>"$out/errors/tcp_trace.err" & tpid=$!
sleep 5

start=$(date +%s)
echo "Installing $pkg ..."
log="$out/${pkg}_install_log.txt"
run() {
    if [ "$mode" = wrap ]; then
        strace -f -ff -o "outputs/$pkg/strace_output_pip" -s 4096 -t -v "$@"
    else
        "$@"
    fi
}
t0=$(date +%s.%N)
# pip flags and the 3-attempt fallback are copied from the authors' trace.sh
run "$venv/bin/pip" install $opts "$spec" --break-system-packages --no-build-isolation --no-cache-dir 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
    echo "First attempt failed, retrying with pip3 ..."
    run "$venv/bin/pip3" install $opts "$spec" 2>&1 | tee "$log"
    status=${PIPESTATUS[0]}
fi
if [ "$status" -ne 0 ]; then
    echo "Second attempt failed, retrying with --break-system-packages ..."
    run "$venv/bin/pip" install $opts "$spec" --break-system-packages 2>&1 | tee "$log"
    status=${PIPESTATUS[0]}
fi

# Logging only: wall-clock seconds pip took (all attempts)
awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN { printf "%.2f
", b - a }' > "$out/install_seconds.txt"

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
sleep 2
# Anything that ignored SIGTERM is killed for sure
kill -KILL $fpid $opid $tpid $mpid 2>/dev/null
cleanup_stale

# An empty strace directory means no system call was recorded: the run is not valid
if [ -z "$(find "outputs/$pkg" -type f -size +0 2>/dev/null | head -1)" ]; then
    warn="$warn strace"
fi

[ "$status" -eq 0 ] && result=Success || result=Failed
echo "$pkg,$result,$(date '+%F %T'),probe_died:${warn:- none}" >> traces/status.csv
echo "[+] Done - $result. eBPF trace: $out | system call trace: outputs/$pkg"
if [ -n "$warn" ]; then
    echo "[!] Probes died early:$warn -> check $out/errors/*.err and re-run"
fi