#!/bin/sh
export WINEDEBUG=-all # disable wine debug output
echo -ne '\033]2;INDRA Rip Tools\007'
script=$(readlink -f "$0")
rootdir=$(dirname "$script")
cd "$rootdir"
python3 -m libraries.tree_diagram
