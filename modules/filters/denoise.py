import vapoursynth as vs

from third_party import havsfunc as haf
from third_party import mvsfunc as mvf

from .utils import ConfigureError, SimpleFilter


@SimpleFilter
def SMDegrain(core, clip, _):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=False)
    return haf.SMDegrain(
        dei16,
        tr=4,
        thSAD=300,
        thSCD1=1200,
        blksize=16,
        search=5,
        prefilter=4,
        contrasharp=True,
        RefineMotion=True,
        pel=2,
        truemotion=False,
        hpad=16,
        vpad=16, )


@SimpleFilter
def SMDegrainFast(core, clip, _):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=False)
    return haf.SMDegrain(
        dei16,
        tr=2,
        blksize=32,
        overlap=16,
        prefilter=4,
        contrasharp=30,
        RefineMotion=True,
        pel=1,
        truemotion=True,
        hpad=0,
        vpad=0, )


@SimpleFilter
def BM3D(core, clip, _, strength, radius, profile):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="limited", filter_param_a=0, filter_param_b=0.5)
    den = mvf.BM3D(
        rgbs,
        sigma=strength,
        radius1=radius,
        profile1=profile,
        refine=1, )
    return core.resize.Bicubic(den, format=vs.YUV444P16, matrix_s="709", range_in_s="limited", range_s="limited", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")


@SimpleFilter
def Waifu2xNCNN(core, clip, _, noise, block, model, gpu, multi_threads, precision=16):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="limited", filter_param_a=0, filter_param_b=0.5)
    def create_filter(clip, gpu):
        return core.w2xnvk.Waifu2x(
            clip,
            noise=noise,
            scale=1,
            tile_size=block,
            model=model,
            precision=precision,
            gpu_id=gpu,
            gpu_thread=multi_threads['threads_per_device'])
    if not multi_threads:
        multi_threads = {'devices': 1, 'threads_per_device': 1}
        exp = create_filter(rgbs, gpu)
    else:
        if not multi_threads['devices'] == 1:
            raise ConfigureError('Waifu2xNCNN: multi_threads: devices can not set other than 1')
        exp = create_filter(rgbs, gpu)
    yuv = mvf.ToYUV(exp, css="444", full=False)
    yuv = mvf.Depth(yuv, depth=16, fulls=False, fulld=False, dither=3)
    return core.resize.Bicubic(yuv, format=vs.YUV444P16, matrix_s="709", range_in_s="limited", range_s="limited", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")


@SimpleFilter
def Waifu2xCaffe(core, clip, _, noise, block_w, block_h, model, cudnn, processor, tta, batch, multi_threads):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="limited", filter_param_a=0, filter_param_b=0.5)
    def create_filter(clip, processor):
        return core.caffe.Waifu2x(
            clip,
            noise=noise,
            scale=1,
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
    yuv = mvf.Depth(yuv, depth=16, fulls=False, fulld=False, dither=3)
    return core.resize.Bicubic(yuv, format=vs.YUV444P16, matrix_s="709", range_in_s="limited", range_s="limited", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")


@SimpleFilter
def Waifu2xW2XC(core, clip, _, noise, block, model_photo, processor, gpu, list_gpu):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="limited", filter_param_a=0, filter_param_b=0.5)
    exp = core.w2xc.Waifu2x(
        rgbs,
        noise=noise,
        scale=1,
        block=block,
        photo=model_photo,
        processor=processor,
        gpu=gpu,
        list_proc=list_gpu, )
    yuv = mvf.ToYUV(exp, css="444", full=False)
    yuv = mvf.Depth(yuv, depth=16, fulls=False, fulld=False, dither=3)
    den16 = core.resize.Bicubic(yuv, format=vs.YUV444P16, matrix_s="709", range_in_s="limited", range_s="limited", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    if not list_gpu:
        dei16 = core.resize.Bicubic(clip, format=vs.YUV444P16, matrix_s="709", range_in_s="limited", range_s="limited", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
        return core.rgvs.Repair(den16, dei16, mode=1)
    return den16


@SimpleFilter
def NLMeans(core, clip, _, strength=1.2, tr=1, sr=2, nr=4, channel="auto", device_type="auto", device_id=0, info=False):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=False)
    return core.knlm.KNLMeansCL(
        dei16,
        d=tr,
        a=sr,
        s=nr,
        h=strength,
        channels=channel,
        device_type=device_type,
        device_id=device_id,
        info=info, )


@SimpleFilter
def VagueDenoiser(core, clip, _, strength, nsteps, csp):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS, fulls=False)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=False, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=False)
    return core.vd.VagueDenoiser(
        dei16,
        threshold=strength,
        method=2,
        nsteps=nsteps,
        percent=csp, )

