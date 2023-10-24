import json
import vapoursynth as vs

from third_party import mvsfunc as mvf

from .utils import ConfigureError, SimpleFilter


@SimpleFilter
def SVP(core, clip, _, super_params, analyse_params, smoothfps_params):
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

