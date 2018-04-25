#!/usr/bin/env python3

from typing import List
import subprocess
from subprocess import Popen
import logging
from . import info

logger = logging.getLogger('tree_diagram')

def invokePipeline(pipeline: List[List[str]]) -> None:
    processes = []
    for cmd in pipeline:
        logger.debug(f'Invoking: {cmd}')
    for cmd in pipeline:
        if info.system == 'Linux' and cmd[0] in info.binaries:
            bininfo = info.binaries[cmd[0]]
            if bininfo['fileformat'] == 'PE' or (bininfo['fileformat'] == 'ELF' and 'libwine.so.1' in bininfo['dependencies']):
                cmd = [info.WINE] + cmd
        stdin = processes[-1].stdout if len(processes) > 0 else None
        stdout = subprocess.PIPE if len(processes) < len(pipeline) - 1 else None
        processes.append(Popen(args=cmd, stdin=stdin, stdout=stdout, bufsize=0))
        if stdin:
            stdin.close()
    try:
        processes[-1].wait()
    finally:
        # last process exited or external interruption, terminate all processes if still running
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
