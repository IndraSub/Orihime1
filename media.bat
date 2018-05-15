@ECHO OFF
CHCP 65001
MODE CON COLS=120
PUSHD %~dp0
TITLE INDRA Rip Tools
python -m libraries.tree_diagram
POPD
PAUSE