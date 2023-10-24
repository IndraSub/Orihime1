# bootstrap main module for embedded Python interpreter
# this should have the same effect as running "python -m modules.tree_diagram"

import runpy
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
        runpy.run_module('modules.tree_diagram', run_name="__main__", alter_sys=True)
