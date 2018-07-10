import vapoursynth as vs
import functools
import math

from .utils import ConfigureError

class FrameRate:
    def __init__(self, _, fps_num, fps_den):
        self.target_fps_num = fps_num
        self.target_fps_den = fps_den

    def __call__(self, core, clip):
        source_clip = clip
        target_fps_num = self.target_fps_num
        target_fps_den = self.target_fps_den
        
        def frame_adjuster(n, clip, target_fps_num, target_fps_den):
            real_n = math.floor(n / (target_fps_num / target_fps_den * clip.fps_den / clip.fps_num))
            one_frame_clip = clip[real_n] * (len(clip) + 100)
            return one_frame_clip
        
        attribute_clip = core.std.BlankClip(source_clip, length=math.floor(len(source_clip) * target_fps_num / target_fps_den * source_clip.fps_den / source_clip.fps_num), fpsnum=target_fps_num, fpsden=target_fps_den)
        adjusted_clip = core.std.FrameEval(attribute_clip, functools.partial(frame_adjuster, clip=source_clip, target_fps_num=target_fps_num, target_fps_den=target_fps_den))
        return core.std.AssumeFPS(adjusted_clip, fpsnum=target_fps_num, fpsden=target_fps_den)
