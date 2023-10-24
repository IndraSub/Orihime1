from vapoursynth_tools import havsfunc as haf

from .utils import SimpleFilter


@SimpleFilter
def HQDeringmod(core, clip, _, threshold=60, inpand=1, edge_expand=1, edge_smooth=1, planes=[0]):
    return haf.HQDeringmod(clip, mrad=edge_expand, msmooth=edge_smooth, mthr=threshold, minp=inpand, planes=planes)


@SimpleFilter
def LGhost(core, clip, _, mode, shift, strength, planes=[0]):
    return core.lghost.LGhost(clip, mode, shift, strength, planes)
