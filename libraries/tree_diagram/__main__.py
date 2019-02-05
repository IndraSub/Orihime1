#!/usr/bin/env python3

from .. import tree_diagram # pylint: disable=relative-beyond-top-level

try:
    tree_diagram.main()
except tree_diagram.ExitException as e:
    exit(e.code)
