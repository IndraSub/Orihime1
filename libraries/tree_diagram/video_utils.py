#!/usr/bin/env python3

import subprocess
import xml.etree.ElementTree as ET
import os

from . import info
from .kit import assertFileWithExit
from .process_utils import invokePipeline

def exportTimecodeMP4(source: str, exportedTimecode: str) -> None:
    print('TreeDiagram [Video Utils] Exporting timecodes from MP4 file...')
    invokePipeline([
        [info.MP4FPSMOD, '-p', exportedTimecode, source]
    ])
    assertFileWithExit(exportedTimecode)
