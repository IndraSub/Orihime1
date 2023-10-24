from third_party import finesharp as fs

from .utils import ConfigureError, SimpleFilter


@SimpleFilter
def FineSharp(core, clip, _, strength, final):
    strength = float(strength)
    final = float(final)
    if final >= 0.25:
        message = 'FineSharp: final XSharpen\'s threshold should small than 0.25 (currently ' + str(final) + ')'
        raise ConfigureError(message)
    return fs.sharpen(clip, sstr=strength, xstr=final)


@SimpleFilter
def CAS(core, clip, _, strength=0.5, planes=[0]):
    return core.cas.CAS(clip, strength, planes)
