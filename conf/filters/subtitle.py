import time
import vapoursynth as vs
from vapoursynth_tools import mvsfunc

from .utils import get_working_directory, merge_clips


class Subtitle:
    def __init__(self, file, texts=None):
        self.file = get_working_directory(file)
        self.texts = texts or []

    def __call__(self, core, clip):
        clip = core.fmtc.resample(clip, css="420", fulls=True)
        frames = core.vsfm.TextSubMod(clip, self.file)
        date = time.strftime('%Y-%m-%d %X', time.gmtime(time.time()))
        framenum = str(frames.num_frames)
        if len(self.texts):
            replaced = [
                core.text.Text(frames[idx], text.format(date, framenum))
                for idx, text in enumerate(self.texts)
            ]
            replaced.append(core.std.Trim(frames, len(self.texts)))
            return merge_clips(replaced)
        return frames
