from .utils import ConfigureError, SimpleFilter, _saved_clips

@SimpleFilter
def StoreClip(core, clip, configure, name):
    _saved_clips[name] = clip
    return clip

@SimpleFilter
def LoadClip(core, clip, configure, name):
    if name not in _saved_clips:
        raise ConfigureError(f"Clip '{name}' not found.")
    return _saved_clips[name]

