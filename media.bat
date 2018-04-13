@ECHO OFF
CHCP 65001
MODE CON COLS=127
TITLE INDRA Rip Tools
PowerShell -ExecutionPolicy Unrestricted .\%~n0.ps1
PAUSE