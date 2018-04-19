import os
import vapoursynth as vs

from vapoursynth_tools import havsfunc as haf
from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError


def SMDegrain(core, clip):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=True)
    den16 = haf.SMDegrain(
        dei16,
        tr=4,
        thSAD=300,
        thSCD1=1200,
        blksize=16,
        search=5,
        prefilter=2,
        contrasharp=20,
        RefineMotion=True,
        pel=2,
        truemotion=False,
        hpad=16,
        vpad=16, )
    rep16 = core.rgvs.Repair(den16, dei16, mode=1)
    return rep16


def SMDegrainFast(core, clip):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=True)
    den16 = haf.SMDegrain(
        dei16,
        tr=2,
        blksize=32,
        overlap=16,
        prefilter=2,
        contrasharp=30,
        RefineMotion=True,
        pel=1,
        truemotion=True,
        hpad=0,
        vpad=0, )
    rep16 = core.rgvs.Repair(den16, dei16, mode=1)
    return rep16


def BM3D(core, clip, strength, radius, profile):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="full", filter_param_a=0, filter_param_b=0.5)
    den = mvf.BM3D(
        rgbs,
        sigma=strength,
        radius1=radius,
        profile1=profile,
        refine=1, )
    dei16 = core.resize.Bicubic(clip, format=vs.YUV444P16, matrix_s="709", range_in_s="full", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    den16 = core.resize.Bicubic(den, format=vs.YUV444P16, matrix_s="709", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    rep16 = core.rgvs.Repair(den16, dei16, mode=1)
    return rep16


def Waifu2xCaffe(core, clip, noise, block, model, cudnn, processor, tta, multi_threads):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="full", filter_param_a=0, filter_param_b=0.5)
    def create_filter(processor):
        return core.caffe.Waifu2x(
            rgbs,
            noise=noise,
            scale=1,
            block_w=block,
            block_h=block,
            model=model,
            cudnn=cudnn,
            processor=processor,
            tta=tta, )
    if not multi_threads:
        exp = create_filter(processor)
    else:
        threads_per_device = multi_threads['threads_per_device']
        devices = multi_threads['devices']
        threads = threads_per_device * devices
        exps = [
            create_filter(p)
            for i in range(0, threads_per_device)
            for p in range(0, devices)
        ]
        exp = core.std.FrameEval(exps[0], lambda n: exps[n % threads])
    yuv = mvf.ToYUV(exp, css="444", full=False)
    yuv = mvf.Depth(yuv, depth=16, fulls=True, fulld=True, dither=3)
    dei16 = core.resize.Bicubic(clip, format=vs.YUV444P16, matrix_s="709", range_in_s="full", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    den16 = core.resize.Bicubic(yuv, format=vs.YUV444P16, matrix_s="709", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    rep16 = core.rgvs.Repair(den16, dei16, mode=1)
    return rep16


def Waifu2xW2XC(core, clip, noise, block, model_photo, processor, gpu, list_gpu):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="full", filter_param_a=0, filter_param_b=0.5)
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
    yuv = mvf.Depth(yuv, depth=16, fulls=True, fulld=True, dither=3)
    den16 = core.resize.Bicubic(yuv, format=vs.YUV444P16, matrix_s="709", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    if not list_gpu:
        dei16 = core.resize.Bicubic(clip, format=vs.YUV444P16, matrix_s="709", range_in_s="full", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
        return core.rgvs.Repair(den16, dei16, mode=1)
    return den16


def VagueDenoiser(core, clip, strength, nsteps, csp):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=True)
    den16 = core.vd.VagueDenoiser(
        dei16,
        threshold=strength,
        method=2,
        nsteps=nsteps,
        percent=csp, )
    rep16 = core.rgvs.Repair(den16, dei16, mode=1)
    return rep16


def MisakaDenoise(core, clip, v_strength, v_nsteps, v_csp, b_strength, b_radius, b_profile):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    dei16 = mvf.Depth(clip, depth=16, fulls=True)
    den1 = core.vd.VagueDenoiser(dei16, threshold=v_strength, method=2, nsteps=v_nsteps, percent=v_csp)
    rgbs = core.resize.Bicubic(den1, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="full", filter_param_a=0, filter_param_b=0.5)
    den2 = mvf.BM3D(
        rgbs,
        sigma=b_strength,
        radius1=b_radius,
        profile1=b_profile,
        refine=1, )
    dei16 = core.resize.Bicubic(clip, format=vs.YUV444P16, matrix_s="709", range_in_s="full", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    den16 = core.resize.Bicubic(den2, format=vs.YUV444P16, matrix_s="709", range_s="full", filter_param_a=0, filter_param_b=0.5, dither_type="error_diffusion")
    rep16 = core.rgvs.Repair(den16, dei16, mode=1)
    return rep16


methods = {
    'SMDegrainFast': SMDegrainFast,
    'SMDegrain': SMDegrain,
    'BM3D': BM3D,
    'Waifu2xCaffe': Waifu2xCaffe,
    'Waifu2xW2XC': Waifu2xW2XC,
    'VagueDenoiser': VagueDenoiser,
    'MisakaDenoise': MisakaDenoise,
}


class Denoise:
    def __init__(self, method, params):
        if method not in methods:
            message = 'Denoise: %r method not found (supports %s)' % (
                method,
                ', '.join(methods.keys()), )
            raise ConfigureError(message)
        self.method = method
        self.params = params

    def __call__(self, core, clip):
        return methods[self.method](core, clip, **self.params)
