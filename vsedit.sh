#!/bin/bash
export WINEDEBUG=-all # disable wine debug output
echo -ne '\033]2;INDRA Rip Tools\007'
script="$(readlink -f "$0")"
rootdir="$(dirname "$script")"
cd "$rootdir"
python3.6 -m libraries.tree_diagram vsedit
sleep 1
read -rsn1 -p "Press any key to continue . . . "; echo
