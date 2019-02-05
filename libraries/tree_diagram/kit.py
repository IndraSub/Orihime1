#!/usr/bin/env python3

from typing import List
from datetime import datetime
import os
import unicodedata
import logging

logger = logging.getLogger('tree_diagram')

class ExitException(Exception):
    def __init__(self, code):
        super().__init__(f'Exit on code: {code}')
        self.code = code

def writeEventName(title: str) -> None:
    print('-' * 120)
    print(f'[{datetime.now().isoformat()}] {title}')
    print('-' * 120)

def assertFileWithExit(filename: str) -> None:
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        logger.critical(f'Failed operation detected, press anykey to exit')
        raise ExitException(-1)

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
