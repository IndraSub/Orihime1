import os
import vapoursynth as vs

from vapoursynth_tools import havsfunc as haf
from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError, SimpleFilter


@SimpleFilter
def Waifu2xExpand(core, clip, _, scale, noise, block_w, block_h, model, cudnn, processor, tta, batch, multi_threads):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="limited", filter_param_a=0, filter_param_b=0.5)
    def create_filter(clip, processor):
        return core.caffe.Waifu2x(
            rgbs,
            noise=noise,
            scale=scale,
            block_w=block_w,
            block_h=block_h,
            model=model,
            cudnn=cudnn,
            processor=processor,
            tta=tta,
            batch=batch)
    if not multi_threads:
        exp = create_filter(rgbs, processor)
    else:
        threads_per_device = multi_threads['threads_per_device']
        devices = multi_threads['devices']
        threads = threads_per_device * devices
        exp = core.std.Interleave([
            create_filter(rgbs.std.SelectEvery(cycle=threads, offsets=i * devices + p), p)
            for i in range(0, threads_per_device)
            for p in range(0, devices)
        ]) if threads > 1 else create_filter(rgbs, processor)
    yuv = mvf.ToYUV(exp, css="444", full=False)
    yuv = mvf.Depth(yuv, depth=10, fulls=False, fulld=False, dither=3)
    return yuv

