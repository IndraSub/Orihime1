from .utils import ConfigureError, SimpleFilter

@SimpleFilter
def Interleave(core, clip, _, _clip):
    return core.std.Interleave(clips=[_clip['raw'], clip])


