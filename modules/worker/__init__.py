#!/usr/bin/env python3

import os

import modules.tree_diagram as tree_diagram
from modules.tree_diagram import info

from .worker import Worker

def main():
    worker = Worker()
    worker.load_config(os.path.join(info.root_directory, 'worker_config.yaml'))
    worker.register()
    worker.run()
