import vapoursynth as vs
from third_party import finesharp as fs
from third_party import havsfunc as haf
from third_party import mvsfunc as mvf

from .utils import ConfigureError

class LineClearness:
    def __init__(self, _, strength=24, thinning=16):
        self.strength = strength
        self.thinning = thinning
    def __call__(self, core, clip):
        w = clip.width
        h = clip.height
        if (clip.height * 2) % 16 != 0:
            message = 'LineClearness: clip size (' + str(w) + ',' + str(h) + ') does not satisfy the requirement of SangNomMod.'
            raise ConfigureError(message)

        topaa1 = core.nnedi3.nnedi3(clip, field=1, dh=True)
        topaa1 = topaa1.resize.Spline36(w, h)
        topaa1 = topaa1.std.Transpose()
        topaa1 = topaa1.resize.Spline36(h * 2, w * 2)

        topaa2 = fs.sharpen(topaa1, sstr=1.6)
        topaa2 = fs.sharpen(topaa2, sstr=1.4)

        topaa3 = core.sangnom.SangNom(topaa2, order=1, aa=[48, 48, 48])
        topaa3 = topaa3.resize.Spline36(h, w)
        topaa3 = topaa3.std.Transpose()

        dark1 = haf.FastLineDarkenMOD(topaa3, strength=self.strength, luma_cap=207, threshold=3, thinning=self.thinning)
        dark2 = core.std.Convolution(dark1, matrix=[1, 2, 1, 2, 4, 2, 1, 2, 1])

        diff_clip = core.rgvs.Repair(core.std.MakeDiff(dark1, dark2), core.std.MakeDiff(clip, dark1), 13)

        csharp = core.std.MergeDiff(dark1, diff_clip)
        edge = core.std.ShufflePlanes(clips=[csharp, clip], planes=[0, 1, 2], colorfamily=vs.YUV)
        aamask = core.std.Prewitt(edge, planes=[1, 2])
        aamask = aamask.std.Expr(expr='x 32 <= 0 x 1.4 pow ?')
        aamask = aamask.std.Median()
        aamask = aamask.std.Inflate()
        return core.std.MaskedMerge(clip, edge, aamask, planes=0)
