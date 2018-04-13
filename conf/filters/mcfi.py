import json
import vapoursynth as vs

from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError


def svp(core, clip, super_params, analyse_params, smoothfps_params):
    clip = core.fmtc.resample(clip, css="420", csp=vs.YUV420P16)
    clip = mvf.Depth(clip, depth=8, fulls=True)
    svp_super = core.svp1.Super(
        clip,
        json.dumps(super_params), )
    vectors = core.svp1.Analyse(
        svp_super['clip'],
        svp_super['data'],
        clip,
        json.dumps(analyse_params), )
    smooth = core.svp2.SmoothFps(
        clip,
        svp_super['clip'],
        svp_super['data'],
        vectors['clip'],
        vectors['data'],
        json.dumps(smoothfps_params), )
    smooth = core.std.AssumeFPS(
        smooth,
        fpsnum=smooth.fps_num,
        fpsden=smooth.fps_den, )
    return smooth


methods = {
    'SVP': svp,
}


class MCFI:
    def __init__(self, method, params):
        if method not in methods:
            message = 'MCFI: %r method not found (supports %s)' % (
                method,
                ', '.join(methods.keys()), )
            raise ConfigureError(message)
        self.method = method
        self.params = params

    def __call__(self, core, clip):
        return methods[self.method](core, clip, **self.params)
