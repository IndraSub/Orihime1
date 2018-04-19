#!/bin/sh
export WINEDEBUG=-all # disable wine debug output
export LANG=en_US.UTF-8
echo -ne '\033]2;INDRA Rip Tools\007'
script=$(readlink -f "$0")
rootdir=$(dirname "$script")
cd "$rootdir"
python3 -m conf.libraries.tree_diagram