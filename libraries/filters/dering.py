from vapoursynth_tools import havsfunc as haf


class Dering:
    def __call__(self, core, clip):
        return haf.HQDeringmod(
            clip,
            mrad=1,
            msmooth=1,
            incedge=False,
            mthr=60,
            minp=1,
            nrmode=2,
            sharp=1,
            drrep=24,
            thr=12,
            planes=[0], )
