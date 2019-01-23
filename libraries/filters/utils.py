import os
import sys
import inspect
import .store as store

class ConfigureError(Exception):
    pass

def SimpleFilter(filter_function):
    def initializer(configure, *args, **kwargs):
        def caller(core, clip):
            kw = dict(kwargs)
            argnames = inspect.getfullargspec(filter_function).args
            for argname in set(argnames[3+len(args):]) - kw.keys():
                stored = store.load_clip(argname)
                if stored is not None:
                    kw[argname] = stored
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
