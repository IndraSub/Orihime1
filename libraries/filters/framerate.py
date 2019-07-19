import vapoursynth as vs
import functools
import math
import os

from .utils import ConfigureError, SimpleFilter, load_info

@SimpleFilter
def FrameRate(core, clip, _, fps_num, fps_den):
    source_clip = clip
    target_fps_num = fps_num
    target_fps_den = fps_den

    def frame_adjuster(n, clip, target_fps_num, target_fps_den):
        real_n = math.floor(n / (target_fps_num / target_fps_den * clip.fps_den / clip.fps_num))
        one_frame_clip = clip[real_n] * (len(clip) + 100)
        return one_frame_clip

    attribute_clip = core.std.BlankClip(source_clip, length=math.floor(len(source_clip) * target_fps_num / target_fps_den * source_clip.fps_den / source_clip.fps_num), fpsnum=target_fps_num, fpsden=target_fps_den)
    adjusted_clip = core.std.FrameEval(attribute_clip, functools.partial(frame_adjuster, clip=source_clip, target_fps_num=target_fps_num, target_fps_den=target_fps_den))
    return core.std.AssumeFPS(adjusted_clip, fpsnum=target_fps_num, fpsden=target_fps_den)

@SimpleFilter
def VFRToCFR(core, clip, _, fps_num, fps_den, drop_frames):
    info = load_info()
    timecode = os.path.join(info['temporary'], 'timecode.txt')
    return core.vfrtocfr.VFRToCFR(clip, timecodes=timecode, fpsnum=fps_num, fpsden=fps_den, drop=drop_frames)
