from vapoursynth_tools import havsfunc as haf


class Dering:
    def __init__(self, _, threshold=60):
        self.threshold = threshold

    def __call__(self, core, clip):
        return haf.HQDeringmod(
            clip,
            mrad=1,
            msmooth=1,
            incedge=False,
            mthr=self.threshold,
            minp=1,
            nrmode=2,
            sharp=1,
            drrep=24,
            thr=12,
            planes=[0], )
