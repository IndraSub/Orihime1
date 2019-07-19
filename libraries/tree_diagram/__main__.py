#!/usr/bin/env python3

import sys

from .. import tree_diagram # pylint: disable=relative-beyond-top-level

try:
    if len(sys.argv) >= 2 and sys.argv[1] == 'vsedit':
        tree_diagram.genVsedit()
    else:
        tree_diagram.main()
except tree_diagram.ExitException as e:
    exit(e.code)
