#!/bin/bash
export WINEDEBUG=-all # disable wine debug output
export LC_ALL=zh_CN.UTF-8
echo -ne '\033]2;INDRA Rip Tools\007'
script="$(readlink -f "$0")"
rootdir="$(dirname "$script")"
cd "$rootdir"
python3.6 -m libraries.worker
sleep 1
