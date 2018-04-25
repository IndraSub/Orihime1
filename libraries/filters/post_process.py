from vapoursynth_tools import havsfunc as haf

from .utils import ConfigureError


def IT(core, clip, fps):
    return core.it.IT(clip, fps=fps, threshold=20, pthreshold=75)


def VIVTC(core, clip, field_order, mode):
    matched_clip = core.vivtc.VFM(clip, order=field_order, mode=mode)
    deinterlaced_clip = core.eedi3.eedi3(matched_clip, field=1)
    callback = lambda n, f: deinterlaced_clip if f.props['_Combed'] > 0 else matched_clip
    processed_clip = core.std.FrameEval(
        matched_clip, callback, prop_src=matched_clip)
    return core.vivtc.VDecimate(processed_clip)


def TIVTC(core, clip, field_order, matching_mode, process_speed,
          post_process_mode):
    tfm = core.avs.TFM(
        clip,
        order=field_order,
        mode=matching_mode,
        slow=process_speed,
        PP=post_process_mode, )
    return core.avs.TDecimate(tfm)


def QTGMC(core, clip, field_order, frame_rate_divisor):
    args = dict(
        Preset='Very Slow',
        InputType=0,
        Border=False,
        Precise=False,
        TFF=field_order,
        FPSDivisor=frame_rate_divisor,
        TR0=2,
        TR1=2,
        TR2=3,
        ChromaMotion=True,
        TrueMotion=False,
        Sharpness=1.0,
        SMode=3,
        SLMode=1,
        SourceMatch=3,
        Lossless=1,
        NoiseProcess=0, )
    return haf.QTGMC(clip, **args)


methods = {
    'IT': IT,
    'VIVTC': VIVTC,
    'TIVTC': TIVTC,
    'QTGMC': QTGMC,
}


class PostProcess:
    def __init__(self, method, params):
        if method not in methods:
            message = 'PostProcess: %r method not found (supports %s)' % (
                method,
                ', '.join(methods.keys()), )
            raise ConfigureError(message)
        self.method = method
        self.params = params

    def __call__(self, core, clip):
        return methods[self.method](core, clip, **self.params)
