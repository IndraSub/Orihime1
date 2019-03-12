#!/usr/bin/env python3

import time
import logging
import pathlib
import os
import subprocess
import hashlib
import threading
import yaml
import requests

import libraries.tree_diagram as tree_diagram
from tree_diagram import info, ExitException

logger = logging.getLogger('tree_diagram:worker')

class Worker:
    def __init__(self):
        self.config = { # default config
            'PollingInterval': 15,
            'Heartbeat': 15,
        }
        self.ep = None
        self.token = None
        self.client_id = None
        self.heartbeat_thread = None
        self.task_id = None

    def load_config(self, filepath):
        with open(filepath) as f:
            config = yaml.load(f)
        if self.config is None:
            config = {}
        self.config = {**self.config, **config}
        self.ep = self.config['Endpoint'].rstrip('/')
        self.token = self.config['Token']

    def register(self):
        client_info = {k: info[k] for k in ['node', 'system', 'system_version', 'root_directory']}
        r = requests.post(self.ep + '/client', data={
            'token': self.token,
            'client_info': client_info
        })
        if r.status_code != 200:
            raise Exception('Failed to register the worker')
        self.client_id = r.json()['client_id']

    def task_status(self, status):
        assert requests.put(self.ep + f'/task/{self.task_id}', data={
            'client_id': self.client_id,
            'status': status
        }).status_code == 200
    def task_fail(self):
        try:
            self.task_status('fail')
        except Exception:
            pass

    def run(self):
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        while True:
            try:
                logger.info('Polling new task')
                r = requests.get(self.ep + '/task', params={
                    'client_id': self.client_id,
                })
                if r.status_code != 200:
                    logger.warning('Failed to fetch new task')
                    continue
                task = r.json()
                if task is None:
                    logger.info('No new task')
                    continue
                self.task_id = task['task_id']

                self.task_status('prepare')
                logger.info('Downloading files')
                for d in task['downloads']:
                    self.download(d['url'], d['path'], d['sha256sum'])
                logger.info('Running prescripts')
                for s in task['prescript']:
                    self.shell(s)

                logger.info('Running task')
                info.content = task['content']
                self.task_status('run')
                tree_diagram.precheckOutput()
                tree_diagram.precheckSubtitle()
                tree_diagram.precleanTemporaryFiles()
                tree_diagram.runMission()

                self.task_status('finalize')
                logger.info('Finishing task')
                for s in task['postscript']:
                    self.shell(s)

                logger.info('Task completed')
                self.task_status('complete')

            except ExitException as e:
                logger.error(f'Mission exited with error code {e.code}')
                logger.debug(f'Running task:')
                logger.debug(yaml.dump(task, default_flow_style=False))
                self.task_fail()
            except Exception as e:
                logger.error(e)
                logger.debug(f'Running task:')
                logger.debug(yaml.dump(task, default_flow_style=False))
                self.task_fail()
            finally:
                self.task_id = None
                time.sleep(self.config['PollingInterval'])

    def download(self, url, path, sha256sum):
        path = os.path.join(info.working_directory, **path.split('/'))
        pathlib.Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        if url.startswith('http://') or url.startswith('https://'):
            with requests.get(url, stream=True) as r:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
                            h.update(chunk)
        else:
            raise Exception(f'Unknown url: {url}')
        assert sha256sum.lower() == h.hexdigest()

    def shell(self, command):
        process = subprocess.Popen(command, shell=True)
        process.wait()
        if process.returncode != 0:
            raise Exception(f'Command exited with code {process.returncode}: {command}')

    def heartbeat(self):
        pass
