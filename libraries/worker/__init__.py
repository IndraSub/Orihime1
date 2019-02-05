#!/usr/bin/env python3

import os
import json
import yaml
import requests

import libraries.tree_diagram as tree_diagram
from tree_diagram import info

class Worker:
    def __init__(self):
        self.config = None
        self.ep = None
        self.client_id = None
    
    def load_config(self, filepath):
        with open(filepath) as f:
            self.config = yaml.load(f)
        if self.config is None:
            raise Exception('Worker config is empty')
        self.ep = self.config['endpoint'].rstrip('/')

    def register(self):
        client_info = {k: info[k] for k in ['node', 'system', 'system_version', 'root_directory']}
        r = requests.post(self.ep + '/client', data={
            'token': self.config['token'],
            'client_info': client_info
        })
        if r.code != 200:
            raise Exception('Failed to register the worker')
        self.client_id = r.json()['client_id']

def main():
    worker = Worker()
    worker.load_config(os.path.join(info.root_directory, 'worker_config.yaml'))
    worker.register()
