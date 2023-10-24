from third_party import vsdehalo as dehalo

from .utils import SimpleFilter


@SimpleFilter
def FineDehalo(core, clip, _, rx=2.0, ry=2.0, darkstr=1.0, brightstr=1.0, lowsens=50, highsens=50, thmi=80, thma=128, thlimi=50, thlima=100, planes=[0]):
    return dehalo.fine_dehalo(clip, rx, ry, darkstr, brightstr, lowsens, highsens, thmi, thma, thlimi, thlima, planes)


@SimpleFilter
def LGhost(core, clip, _, mode, shift, strength, planes=[0]):
    return core.lghost.LGhost(clip, mode, shift, strength, planes)
