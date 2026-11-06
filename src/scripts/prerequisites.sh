#!/bin/bash

sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv strace
sudo apt-get install -y bpfcc-tools linux-headers-$(uname -r)
sudo apt-get install -y linux-tools-$(uname -r)
bpftool --version
uname -r
sudo apt-get install -y bpftrace
bpftrace --version
# Pinned to the versions the models/*.pkl were saved with
pip3 install -r "$(dirname "$0")/../../requirements.txt" --break-system-packages
