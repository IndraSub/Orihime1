#!/usr/bin/env python3

import time
import logging
import pathlib
import os
import subprocess
import hashlib
import threading
import traceback
import yaml
import requests

import modules.tree_diagram as tree_diagram
from modules.tree_diagram import info, ExitException, syncContent

logger = logging.getLogger('tree_diagram:worker')

TASK_STATUS_WAITING = 0
TASK_STATUS_STARTED = 1
TASK_STATUS_RUN = 10
TASK_STATUS_FINALIZE = 90
TASK_STATUS_FINISHED = 100
TASK_STATUS_ERROR = -1

class Worker:
    def __init__(self):
        self.config = { # default config
            'PollingInterval': 15,
            'Heartbeat': 15,
        }
        self.ep = None
        self.token = None
        self.client_id = None
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        self.heartbeat_cond = threading.Condition()
        self.heartbeat_sent = True
        self.task_id = None
        self.status = TASK_STATUS_WAITING
        self.heartbeat_thread.start()

    def load_config(self, filepath):
        with open(filepath) as f:
            config = yaml.safe_load(f)
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
        if r.status_code != 200 or r.json()['code'] != 200:
            raise Exception('Failed to register the worker')
        self.client_id = r.json()['client_id']

    def task_status(self, status):
        with self.heartbeat_cond:
            self.status = status
            self.heartbeat_sent = False
            self.heartbeat_cond.notify_all()
            self.heartbeat_cond.wait_for(lambda: self.heartbeat_sent)

    def task_fail(self):
        try:
            self.task_status(TASK_STATUS_ERROR)
        except Exception:
            pass

    def run(self):
        while True:
            try:
                logger.info('Polling new task')
                r = requests.get(self.ep + '/task', params={
                    'client_id': self.client_id,
                })
                if r.status_code != 200 or r.json()['code'] != 200:
                    logger.warning('Failed to fetch task list')
                    continue
                task_list = r.json()
                if not task_list['task_list']:
                    logger.info('No new task')
                    continue
                with self.heartbeat_cond:
                    self.task_id = task_list['task_list'][0]

                r = requests.post(self.ep + f'/task/{self.task_id}', data={
                    'client_id': self.client_id,
                })
                if r.status_code != 200 or r.json()['code'] != 200:
                    logger.warning('Failed to apply new task')
                    continue

                r = requests.get(self.ep + f'/task/{self.task_id}', params={
                    'client_id': self.client_id,
                })
                if r.status_code != 200 or r.json()['code'] != 200:
                    logger.warning('Failed to fetch new task')
                    continue
                task = r.json()['task_data']

                self.task_status(TASK_STATUS_STARTED)
                logger.info('Downloading files')
                for d in task['downloads']:
                    self.download(d['url'], d['path'], d['sha256sum'])
                logger.info('Running prescripts')
                for s in task['prescript']:
                    self.shell(s)

                self.task_status(TASK_STATUS_RUN)
                logger.info('Running task')
                info.content = task['content']
                info.autorun = True
                syncContent()
                tree_diagram.precheckOutput()
                tree_diagram.precheckSubtitle()
                tree_diagram.precleanTemporaryFiles()
                tree_diagram.runMission()

                self.task_status(TASK_STATUS_FINALIZE)
                logger.info('Finishing task')
                for s in task['postscript']:
                    self.shell(s)

                self.task_status(TASK_STATUS_FINISHED)
                logger.info('Task completed')

            except KeyboardInterrupt:
                logger.info("Ctrl-c pressed, program exit")
                exit(0)
            except ExitException as e:
                logger.error(f'Mission exited with error code {e.code}')
                logger.debug(f'Running task:')
                logger.debug(yaml.dump(task, default_flow_style=False))
                self.task_fail()
            except Exception:
                logger.error(traceback.format_exc())
                logger.debug(f'Running task:')
                logger.debug(yaml.dump(task, default_flow_style=False))
                self.task_fail()
            finally:
                with self.heartbeat_cond:
                    self.task_id = None
                    self.status = TASK_STATUS_WAITING
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
        with self.heartbeat_cond:
            while True:
                self.heartbeat_cond.wait(self.config['Heartbeat'])
                task_id = self.task_id
                if task_id is None:
                    assert self.heartbeat_sent
                    continue
                r = requests.put(self.ep + f'/task/{task_id}', data={
                    'client_id': self.client_id,
                    'task_status': self.status
                })
                if r.status_code != 200 or r.json()['code'] != 200:
                    logger.warning(r.text)
                self.heartbeat_sent = True
                self.heartbeat_cond.notify_all()
