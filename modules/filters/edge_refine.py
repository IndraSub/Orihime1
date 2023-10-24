from third_party import havsfunc as haf
from third_party import muvsfunc as muf
from third_party import mvsfunc as mvf


class EdgeRefine:
    def __init__(self, _):
        pass
    def __call__(self, core, clip):
        deb1 = muf.GradFun3(clip, 0.25)
        deb2 = core.f3kdb.Deband(deb1, 24, 48, 20, 20, output_depth=16)
        tdgm = muf.TEdge(deb2)
        dfrg = core.std.Expr(tdgm, expr='x 65535 *')
        dfrg = dfrg.std.Deflate()
        dfrg = dfrg.std.Convolution(matrix=[1, 1, 1, 1, 1, 1, 1, 1, 1])
        return core.std.MaskedMerge(deb2, clip, dfrg, planes=0)
