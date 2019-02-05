#!/usr/bin/env python3

from .. import tree_diagram

try:
    tree_diagram.main()
except tree_diagram.ExitException as e:
    exit(e.code)
