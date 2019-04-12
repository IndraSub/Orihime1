#!/usr/bin/env python3

import os

import libraries.tree_diagram as tree_diagram
from libraries.tree_diagram import info

from .worker import Worker

def main():
    worker = Worker()
    worker.load_config(os.path.join(info.root_directory, 'worker_config.yaml'))
    worker.register()
    worker.run()
