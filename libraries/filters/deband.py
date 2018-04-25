from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError


def f3kdb(core, clip):
    clip = mvf.Depth(clip, depth=16, fulls=True, dither=3)
    pre16 = core.std.Convolution(clip, matrix=[1, 2, 1, 2, 4, 2, 1, 2, 1])
    pre16 = pre16.std.Convolution(matrix=[1, 1, 1, 1, 1, 1, 1, 1, 1])
    noi16 = core.std.MakeDiff(clip, pre16)
    pre16 = core.std.MakeDiff(clip, noi16)
    deb16 = core.f3kdb.Deband(pre16, output_depth=16)
    deb16 = mvf.LimitFilter(deb16, pre16, ref=pre16, thr=0.30, elast=2.5)
    add16 = core.std.MergeDiff(deb16, noi16)
    return add16


methods = {
    'f3kdb': f3kdb,
}


class Deband:
    def __init__(self, method):
        if method not in methods:
            message = 'Deband: %r method not found (supports %s)' % (
                method,
                ', '.join(methods.keys()), )
            raise ConfigureError(message)
        self.method = method

    def __call__(self, core, clip):
        if self.method in methods:
            return methods[self.method](core, clip)
