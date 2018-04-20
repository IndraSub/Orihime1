import os
import sys

import vapoursynth

from vapoursynth_tools import logonr_vs as logonr

from .utils import ConfigureError, get_working_directory


class Delogo:
    def __init__(self, logo_file, frames):
        if len(frames) == 0:
            raise ConfigureError('Delogo: frames length is 0')
        self.logo_file = get_working_directory(logo_file)
        self.frames = frames

    def __call__(self, core, clip):
        dlg = clip
        for frames in self.get_frames():
            start, end = frames
            print('[DEBUG][Delogo] Frames to be processed: '+str(start)+'-'+str(end), file=sys.stderr)
            dlg = core.delogo.EraseLogo(
                dlg,
                self.logo_file,
                start=start,
                end=end,
                fadein=False,
                fadeout=False)
        core = vapoursynth.get_core()
        return logonr.logoNR(core=core, dlg=dlg, src=clip, chroma=True)

    def get_frames(self):
        frame = 0
        last_frame = 0
        off = [264, 24, 24, 264]
        for index in range(0, 4):
            start, end = self.frames[index]
            last_frame = frame
            frame += int((end - start + 1) / 5 * 4)
            yield last_frame, frame - off[index]
