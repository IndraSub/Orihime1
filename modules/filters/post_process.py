from vapoursynth_tools import CSMOD as _CSMOD

from .utils import ConfigureError, SimpleFilter

@SimpleFilter
def CSMOD(core, clip, _, _clip, preset="very slow"):
    return _CSMOD.CSMOD(filtered=clip, source=_clip['source'], preset=preset, limitsrc=True)


