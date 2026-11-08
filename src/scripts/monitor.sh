#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: monitor.sh <package_name>"
    exit 1
fi

pkg=$1

base="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$base"

out="outputs/${pkg}"
rm -rf "$out"
mkdir -p "$out"

pids="PIDs"
mkdir -p "$pids"
pids_file="${pids}/${pkg}.txt"
rm -f "$pids_file"
touch "$pids_file"

# Logging only (not in the authors' script): how late strace attached to each process.
# delay = uptime at attach - process start time (/proc/<pid>/stat field 22, in clock ticks).
timing="traces/${pkg}/attach_delay.txt"
mkdir -p "traces/${pkg}"
: > "$timing"
hz=$(getconf CLK_TCK)

trap 'pkill -P $$ strace 2>/dev/null; echo "monitor.sh: stopped"; exit 0' INT TERM

# The authors run trace.sh from a shell, so no python process of the harness exists.
# Here main.py / batch.py are python3 processes too: never trace monitor.sh's own ancestors.
skip=" "
p=$$
while [ -n "$p" ] && [ "$p" -gt 1 ]; do
    skip="$skip$p "
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
done

trace() {
    local pid=$1 now st
    now=$(cut -d' ' -f1 /proc/uptime)
    echo "$pid" >> "$pids_file"
    strace -f -ff -o "${out}/${pid}" -s 4096 -t -v -p "$pid" 2>/dev/null &
    echo "Tracing PID $pid ($2)"
    # read after strace is launched, so the logging never delays the attach
    st=$(sed 's/.*) //' "/proc/$pid/stat" 2>/dev/null | awk '{print $20}')
    [ -n "$st" ] && awk -v n="$now" -v s="$st" -v hz="$hz" -v p="$pid" -v c="$2" \
        'BEGIN { print p, c, sprintf("%.2f", n - s / hz) }' >> "$timing"
}

check() {
    case "$skip" in *" $1 "*) return 0 ;; esac
    grep -q "^$1$" "$pids_file"
}

echo "Monitoring package $pkg ..."
while true; do
    for proc in python python3 pip pip3; do
        for pid in $(pgrep -x "$proc"); do
            if ! check "$pid"; then
                trace "$pid" "$proc"
            fi
        done
    done
    sleep "${POLL:-1}"      # authors: 1 s. POLL is only for diagnosing the attach delay
done