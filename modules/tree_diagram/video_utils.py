#!/usr/bin/env python3

from . import info
from .kit import assertFileWithExit
from .process_utils import invokePipeline

def exportTimecodeMP4(source: str, exportedTimecode: str) -> None:
    print('VideoUtils: Exporting timecodes from MP4 file...')
    invokePipeline([
        [info.MP4FPSMOD, '-p', exportedTimecode, source]
    ])
    assertFileWithExit(exportedTimecode)
