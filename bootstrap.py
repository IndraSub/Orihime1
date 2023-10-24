# bootstrap main module for embedded Python interpreter
# this should have the same effect as running "python -m modules.tree_diagram"

import runpy
import sys

sys.path.append(".")
if __name__ == "__main__":
        runpy.run_module('modules.tree_diagram', run_name="__main__", alter_sys=True)
