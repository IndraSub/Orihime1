import os
import vapoursynth as vs

from vapoursynth_tools import havsfunc as haf
from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError


def Waifu2xExpand(core, clip, scale, noise, block, model, cudnn, processor, tta):
    clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444PS)
    clip = core.fmtc.matrix(clip, mat="709", mats="709", matd="709", fulls=True, bits=32)
    rgbs = core.resize.Bicubic(clip, format=vs.RGBS, matrix_in=1, matrix_in_s="709", range_in_s="full", filter_param_a=0, filter_param_b=0.5)
    exp = core.caffe.Waifu2x(
        rgbs,
        noise=noise,
        scale=scale,
        block_w=block,
        block_h=block,
        model=model,
        cudnn=cudnn,
        processor=processor,
        tta=tta, )
    yuv = mvf.ToYUV(exp, css="444", full=False)
    yuv = mvf.Depth(yuv, depth=10, fulls=True, fulld=True, dither=3)
    return yuv


methods = {
    'Waifu2xExpand': Waifu2xExpand
}


class Upscale:
    def __init__(self, method, params):
        if method not in methods:
            message = 'Upscale: %r method not found (supports %s)' % (
                method,
                ', '.join(methods.keys()), )
            raise ConfigureError(message)
        self.method = method
        self.params = params

    def __call__(self, core, clip):
        return methods[self.method](core, clip, **self.params)