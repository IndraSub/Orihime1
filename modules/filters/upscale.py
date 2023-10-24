import os
import vapoursynth as vs

from vapoursynth_tools import havsfunc as haf
from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError, SimpleFilter


@SimpleFilter
def Waifu2xExpandCaffe(core, clip, _, scale, noise, block_w, block_h, model, cudnn, processor, tta, batch, multi_threads=False):
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


@SimpleFilter
def Waifu2xExpandNcnn(core, clip, _, scale, noise, block_w, block_h, model, processor=0, precision=16, batch=0, multi_threads=False):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="limited", filter_param_a=0, filter_param_b=0.5)
    def create_filter(clip, processor):
        return core.w2xnvk.Waifu2x(
            rgbs,
            noise=noise,
            scale=scale,
            tile_size_w=block_w,
            tile_size_h=block_h,
            model=model,
            gpu_id=processor,
            precision=precision,
            gpu_thread=batch)
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


@SimpleFilter
def Anime4K(core, clip, _, scale, passes=2, push_color_count=2, push_color_strength=0.3, push_gradient=1, gpu=1, acnet=0, hdn=0, platform=0, device=0, multi_threads=False):
    def create_filter(clip, platform, device):
        return core.anime4kcpp.Anime4KCPP(
            clip,
            zoomFactor=scale,
            passes=passes,
            pushColorCount=push_color_count,
            strengthColor=push_color_strength,
            strengthGradient=push_gradient,
            ACNet=acnet,
            GPUMode=gpu,
            HDN=hdn,
            platformID=platform,
            deviceID=device)
    if not multi_threads:
        exp = create_filter(clip, platform, device)
    else:
        threads_per_device = multi_threads['threads_per_device']
        devices = multi_threads['devices']
        threads = threads_per_device * devices
        exp = core.std.Interleave([
            create_filter(clip.std.SelectEvery(cycle=threads, offsets=i * devices + p), platform, p)
            for i in range(0, threads_per_device)
            for p in range(0, devices)
        ]) if threads > 1 else create_filter(clip, platform, device)
    return exp

