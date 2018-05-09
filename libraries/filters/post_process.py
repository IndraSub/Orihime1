from vapoursynth_tools import havsfunc as haf

from .utils import ConfigureError, SimpleFilter


@SimpleFilter
def IT(core, clip, _, fps):
    return core.it.IT(clip, fps=fps, threshold=20, pthreshold=75)


@SimpleFilter
def VIVTC(core, clip, _, field_order, mode):
    matched_clip = core.vivtc.VFM(clip, order=field_order, mode=mode)
    deinterlaced_clip = core.eedi3.eedi3(matched_clip, field=1)
    callback = lambda n, f: deinterlaced_clip if f.props['_Combed'] > 0 else matched_clip
    processed_clip = core.std.FrameEval(
        matched_clip, callback, prop_src=matched_clip)
    return core.vivtc.VDecimate(processed_clip)


@SimpleFilter
def TIVTC(core, clip, _, field_order, matching_mode, process_speed,
          post_process_mode):
    tfm = core.avs.TFM(
        clip,
        order=field_order,
        mode=matching_mode,
        slow=process_speed,
        PP=post_process_mode, )
    return core.avs.TDecimate(tfm)


@SimpleFilter
def QTGMC(core, clip, _, field_order, frame_rate_divisor):
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

