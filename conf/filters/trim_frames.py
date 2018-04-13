from .utils import ConfigureError, merge_clips


class TrimFrames:
    def __init__(self, frames):
        if len(frames) == 0:
            raise ConfigureError('TrimFrames: frames length is 0')
        self.frames = frames

    def __call__(self, core, clip):
        clips = [
            core.std.Trim(clip, first=first, last=last)
            for first, last in self.frames
        ]
        return merge_clips(clips)
