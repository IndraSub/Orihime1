#!/usr/bin/env python3

from typing import List, Tuple
import os
import importlib
from datetime import datetime
import logging
import io
import unicodedata
from . import info

logger = logging.getLogger('tree_diagram')

def writeEventName(title: str) -> None:
    print('-' * 126)
    print(f'[{datetime.now().isoformat()}] {title}')
    print('-' * 126)

def getWorkingDirectory() -> str:
    return os.path.join(info.root_directory, 'episodes')

def getWorkListFilePath() -> str:
    import yaml
    path = os.path.join(getWorkingDirectory(), 'missions.yaml')
    if not os.path.exists(path):
        logger.critical(f'{path} not found')
        exit(-1)
    return path

def getMissionFilePath(filename, offset) -> str:
    import yaml
    with open(filename, encoding='utf8') as f:
        worklist = yaml.load(f)
    path = os.path.join(getWorkingDirectory(), worklist['missions'][offset])
    if not os.path.exists(path):
        logger.critical(f'{path} not found')
        exit(-1)
    return path

def getWorkingContent() -> dict:
    import yaml
    with open(getMissionFilePath(getWorkListFilePath(), 0), encoding='utf8') as f: #NOTE: Take value of index 0 is a workaround, will process all indexes in future!
        working = yaml.load(f)
    with open(os.path.join(getWorkingDirectory(), working['project']), encoding='utf8') as f:
        descriptions = yaml.load_all(f)
        working['project'] = next(project for project in descriptions if project['quality'] == working['quality'])
    return working

def assertFileWithExit(filename: str) -> None:
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        logger.critical(f'Failed operation detected, press anykey to exit')
        exit(-1)

def choices(message: str, options: List[str], default_choice: int) -> int:
    '''
    default_choice: set to -1 when there is no default
    '''
    print(message)
    keys = []
    words = []
    prompts = []
    for c in options:
        pos = c.find('&')
        if pos != -1:
            keys.append(c[pos + 1].upper())
            words.append(c[:pos] + c[pos + 1:])
        else:
            keys.append('')
            words.append(c)
        prompts.append(f'[{keys[-1]}] {words[-1]}')        
    prompt = '  '.join(prompts)
    if default_choice != -1:
        prompt += f' (default is "{keys[default_choice]}")'
    prompt += ': '
    while True:
        val = input(prompt).upper()
        if val == '' and default_choice != -1:
            return default_choice
        val = val.strip()
        for i in range(0, len(options)):
            if val == keys[i] or val == words[i].upper():
                return i

def padUnicode(s: str, size: int) -> str:
    l = sum(1 + (unicodedata.east_asian_width(c) in "WF") for c in s)
    if l < size:
        return s + ' ' * (size - l)
    return s
