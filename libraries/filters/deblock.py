import vapoursynth as vs
from vapoursynth_tools import Oyster

from .utils import ConfigureError

class FastDeblock:
    def __init__(self, _, radius_temporal, radius_spatial, h=3.2, lowpass="0.0:0.0 0.48:1024.0 1.0:1024.0"):
        self.radius_temporal = int(radius_temporal)
        self.radius_spatial = int(radius_spatial)
        self.h = float(h)
        self.lowpass = lowpass

    def __call__(self, core, clip):
        if clip.format.color_family != vs.YUV:
            raise ConfigureError('FastDeblock: input must be a Gray or YUV clip!')
        core          = vs.get_core()
        MakeDiff      = core.std.MakeDiff
        MergeDiff     = core.std.MergeDiff
        MaskedMerge   = core.std.MaskedMerge
        ShufflePlanes = core.std.ShufflePlanes
        clip          = core.fmtc.bitdepth(clip, bits=32, fulls=False, fulld=True)
        origin        = clip
        clip          = ShufflePlanes(clip, 0, vs.GRAY)
        colorspace    = clip.format.color_family
        src           = clip
        ref           = Oyster.Basic(clip, None, self.radius_temporal)
        mask          = self.genblockmask(clip)
        cleansed      = self.nlmeans(ref, 0, self.radius_spatial, self.radius_spatial / 2, self.h, ref)
        ref           = self.freq_merge(cleansed, ref, 9, self.lowpass)
        src           = self.freq_merge(cleansed, src, 9, self.lowpass)
        clip          = MaskedMerge(src, ref, mask, first_plane=True)
        clip          = ShufflePlanes([clip, origin, origin], [0, 1, 2], vs.YUV)
        clip          = core.fmtc.bitdepth(clip, bits=16, fulls=True, fulld=False)
        return clip

    def freq_merge(self, low, hi, sbsize, sstring):
        core            = vs.get_core()
        DFTTest         = core.dfttest.DFTTest
        MakeDiff        = core.std.MakeDiff
        MergeDiff       = core.std.MergeDiff
        hif             = MakeDiff(hi, DFTTest(hi, sbsize=sbsize, sstring=sstring, smode=0, sosize=0, tbsize=1, tosize=0, tmode=0))
        clip            = MergeDiff(DFTTest(low, sbsize=sbsize, sstring=sstring, smode=0, sosize=0, tbsize=1, tosize=0, tmode=0), hif)
        return clip

    def genblockmask(self, src):
        core            = vs.get_core()
        Resample        = core.fmtc.resample
        BlankClip       = core.std.BlankClip
        AddBorders      = core.std.AddBorders
        StackHorizontal = core.std.StackHorizontal
        StackVertical   = core.std.StackVertical
        Expr            = core.std.Expr
        CropAbs         = core.std.CropAbs
        clip            = BlankClip(src, 24, 24, color=0.0)
        clip            = AddBorders(clip, 4, 4, 4, 4, color=1.0)
        clip            = StackHorizontal([clip, clip, clip, clip])
        clip            = StackVertical([clip, clip, clip, clip])
        clip            = Resample(clip, 32, 32, kernel="point", fulls=True, fulld=True)
        clip            = Expr(clip, ["x 0.0 > 1.0 0.0 ?"])
        clip            = StackHorizontal([clip, clip, clip, clip, clip, clip, clip, clip])
        clip            = StackVertical([clip, clip, clip, clip, clip, clip])
        clip            = StackHorizontal([clip, clip, clip, clip, clip, clip])
        clip            = StackVertical([clip, clip, clip, clip, clip])
        clip            = StackHorizontal([clip, clip, clip, clip, clip, clip])
        clip            = StackVertical([clip, clip, clip, clip, clip])
        clip            = CropAbs(clip, src.width, src.height, 0, 0)
        return clip

    def nlmeans(self, src, d, a, s, h, rclip):
        core            = vs.get_core()
        Crop            = core.std.CropRel
        KNLMeansCL      = core.knlm.KNLMeansCL
        def duplicate(src):
            if d > 0:
               head     = src[0] * d
               tail     = src[src.num_frames - 1] * d
               clip     = head + src + tail
            else:
               clip     = src
            return clip
        pad             = self.padding(src, a+s, a+s, a+s, a+s)
        pad             = duplicate(pad)
        if rclip is not None:
           rclip        = self.padding(rclip, a+s, a+s, a+s, a+s)
           rclip        = duplicate(rclip)
        nlm             = KNLMeansCL(pad, d=d, a=a, s=s, h=h, wref=1.0, rclip=rclip)
        clip            = Crop(nlm, a+s, a+s, a+s, a+s)
        return clip[d:clip.num_frames - d]

    def padding(self, src, left, right, top, bottom):
        core            = vs.get_core()
        Resample        = core.fmtc.resample
        w               = src.width
        h               = src.height
        clip            = Resample(src, w+left+right, h+top+bottom, -left, -top, w+left+right, h+top+bottom, kernel="point", fulls=True, fulld=True)
        return clip

class OysterDeblock:
    def __init__(self, _, radius=6, sigma=16.0, h=6.4):
        self.radius = int(radius)
        self.sigma = float(sigma)
        self.h = float(h)
    
    def __call__(self, core, clip):
        clip = core.fmtc.bitdepth(clip, bits=32, fulls=False, fulld=True)
        origin = clip
        clip = core.std.ShufflePlanes(clip, 0, vs.GRAY)
        sup = Oyster.Super(clip)
        ref_f = Oyster.Basic(clip, sup, short_time=False)
        ref_s = Oyster.Basic(clip, sup, short_time=True)
        clip = Oyster.Destaircase(clip, ref_f, radius=self.radius, sigma=self.sigma, block_step=2)
        clip = Oyster.Deringing(clip, ref_s, radius=self.radius, sigma=self.sigma, h=self.h, block_step=2)
        clip = core.std.ShufflePlanes([clip, origin, origin], [0, 1, 2], vs.YUV)
        clip = core.fmtc.bitdepth(clip, bits=16, fulls=True, fulld=False)
        return clip
