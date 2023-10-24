#!/usr/bin/env python3

from typing import List
import subprocess
from subprocess import Popen
import logging
from . import info
from .kit import ExitException

logger = logging.getLogger('tree_diagram')

def invokePipeline(pipeline: List[List[str]]) -> None:
    processes = []
    check_exit = []
    for cmd in pipeline:
        if isinstance(cmd, bool):
            check_exit[-1] = cmd
            continue
        logger.debug(f'Invoking: {" ".join(cmd)}')
        if info.system == 'Linux' and cmd[0] in info.binaries:
            bininfo = info.binaries[cmd[0]]
            if bininfo['fileformat'] == 'PE' or (bininfo['fileformat'] == 'ELF' and 'libwine.so.1' in bininfo['dependencies']):
                cmd = [info.WINE] + cmd
        stdin = processes[-1].stdout if len(processes) > 0 else None
        stdout = subprocess.PIPE if len(processes) < len(pipeline) - 1 else None
        processes.append(Popen(args=cmd, stdin=stdin, stdout=stdout, bufsize=0))
        #processes.append(Popen(cmd))
        #processes.append(Popen(args=cmd, stdin=stdin, stderr=subprocess.STDOUT, bufsize=0))
        check_exit.append(False)
        if stdin:
            stdin.close()
    try:
        processes[-1].wait()
    finally:
        # last process exited or external interruption, terminate all processes if still running
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc, check in zip(processes, check_exit):
            code = proc.poll()
            if check and code != 0:
                logger.critical(f'Process exited with {code}: {" ".join(proc.args)}')
                raise ExitException(-1)
