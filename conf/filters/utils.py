import os
import sys


class ConfigureError(Exception):
    pass


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
