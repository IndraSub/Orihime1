import os
import sys

import vapoursynth

from vapoursynth_tools import logonr_vs as logonr

from .utils import ConfigureError, get_working_directory


class Delogo:
    def __init__(self, logo_file, frames, autodetect=False, l=0, r=0, t=0, b=0):
        if len(frames) == 0:
            raise ConfigureError('Delogo: frames length is 0')
        self.logo_file = get_working_directory(logo_file)
        self.frames = self.get_frames(frames)
        self.l = l
        self.r = r
        self.t = t
        self.b = b
        self.autodetect = autodetect
        if not autodetect:
            self.autodetect = 0
        if not isinstance(self.autodetect, int):
            raise Exception(f'[Delogo] Unacceptable autodetect range: {autodetect}')

    def __call__(self, core, clip):
        for frames in self.frames:
            start, end = frames
            print('[DEBUG][Delogo] Frames to be processed: '+str(start)+'-'+str(end), file=sys.stderr)
        dlg = core.delogo.EraseLogo(
            clip,
            self.logo_file,
            fadein=False,
            fadeout=False)
        autodetect = self.autodetect
        frames = self.frames
        auto_dlg = None
        if autodetect:
            auto_dlg = self.auto_delogo(clip, dlg)
        core = vapoursynth.get_core()
        last_end = 0
        def decide(n):
            if last_end != 0 and abs(n - last_end) < autodetect:
                return auto_dlg
            for start, end in frames:
                if n >= start and n <= end:
                    last_end = end
                    return dlg
            return clip
        res = core.std.FrameEval(clip, decide)
        return logonr.logoNR(core=core, dlg=res, src=clip, l=self.l, r=self.r, t=self.t, b=self.b, chroma=True)

    def auto_delogo(self, clip, dlg):
        core = vapoursynth.get_core()
        clip_c = core.std.Crop(clip, left=self.l, right=self.r, top=self.t, bottom=self.b)
        clip_c = core.fmtc.resample(clip_c, css='444')
        clip_e_a = core.tcanny.TCanny(clip_c, mode=1, sigma=0.5, op=2)
        clip_e_y = core.std.ShufflePlanes(clip_e_a, 0, vapoursynth.GRAY)
        clip_e_u = core.std.ShufflePlanes(clip_e_a, 1, vapoursynth.GRAY)
        clip_e_v = core.std.ShufflePlanes(clip_e_a, 2, vapoursynth.GRAY)
        clip_e = core.std.Expr([clip_e_y, clip_e_u, clip_e_v], 'x y max z max')

        dlg_c = core.std.Crop(dlg, left=self.l, right=self.r, top=self.t, bottom=self.b)
        dlg_c = core.fmtc.resample(dlg_c, css='444')
        dlg_e_a = core.tcanny.TCanny(dlg_c, mode=1, sigma=0.5, op=2)
        dlg_e_y = core.std.ShufflePlanes(dlg_e_a, 0, vapoursynth.GRAY)
        dlg_e_u = core.std.ShufflePlanes(dlg_e_a, 1, vapoursynth.GRAY)
        dlg_e_v = core.std.ShufflePlanes(dlg_e_a, 2, vapoursynth.GRAY)
        dlg_e = core.std.Expr([dlg_e_y, dlg_e_u, dlg_e_v], 'x y max z max')

        wlogo = core.std.BlankClip(clip, color=[128,128,128], length=1)
        wlogo = core.delogo.EraseLogo(wlogo, self.logo_file)
        wlogo = core.std.Crop(wlogo, left=self.l, right=self.r, top=self.t, bottom=self.b)
        wlogo = core.std.ShufflePlanes(wlogo, 0, vapoursynth.GRAY)
        logo_e = core.tcanny.TCanny(wlogo, mode=1, sigma=0.5)
        logo_e = logo_e * clip.num_frames

        clip_l = core.std.Expr([clip_e, dlg_e, logo_e], 'x y 1.2 * > x z * 256 / 0 ?')
        dlg_l = core.std.Expr([dlg_e, clip_e, logo_e], 'x y 1.2 * > x z * 256 / 0 ?')

        clip_st = core.std.PlaneStats(clip_l)
        dlg_st = core.std.PlaneStats(dlg_l)

        def decide(n, f):
            clip_avg = f[0].props['PlaneStatsAverage']
            dlg_avg = f[1].props['PlaneStatsAverage']
            if clip_avg * 1.2 < dlg_avg: # 1.2 needs to be further tested
                return clip
            else:
                # when at very bright background or a logo exists but delogo is not very clean,
                # clip_avg ~= dlg_avg
                # so apply delogo
                return dlg
        return core.std.FrameEval(clip, decide, prop_src=[clip_st, dlg_st])

    def get_frames(self, frames):
        frame = 0
        last_frame = 0
        off = [264, 24, 24, 264]
        for index in range(0, 4):
            start, end = frames[index]
            last_frame = frame
            frame += int((end - start + 1) / 5 * 4)
            yield last_frame, frame - off[index]
