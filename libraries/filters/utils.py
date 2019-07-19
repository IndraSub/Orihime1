import os
import sys
import json
import inspect

_saved_clips = {}
_info = None

class ConfigureError(Exception):
    pass

def SimpleFilter(filter_function):
    def initializer(configure, *args, **kwargs):
        def caller(core, clip):
            kw = dict(kwargs)
            if '_clip' in kw:
                for i in kw['_clip']:
                    stored = load_clip(kw['_clip'][i])
                    if stored is not None:
                        kw['_clip'][i] = stored
            return filter_function(core, clip, configure, *args, **kw)
        return caller
    return initializer

def get_working_directory(*paths, is_exists=True):
    path = os.path.dirname(__file__)
    path = os.path.join(path, '..', '..', 'episodes', *paths)
    if is_exists and not os.path.exists(path):
        raise FileNotFoundError('%s not found' % path)
    return os.path.realpath(path)

def merge_clips(clips):
    clip = clips[0]
    for item in clips[1:]:
        clip += item
    return clip

def load_clip(name):
    if name not in _saved_clips:
        return None
    return _saved_clips[name]

def load_info():
    global _info
    if _info is None:
        _info = json.loads(os.environ['TDINFO'])
    return _info
