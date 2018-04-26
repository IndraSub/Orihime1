import sys

from os.path import join, dirname
import os
import platform
import vapoursynth as vs
import json

info = json.loads(os.environ['TDINFO'])

def load_plugins(core):
    path = join(dirname(__file__), '..', '..', 'bin', platform.system().lower(), 'filter_plugins')
    for name in info['vsfilters']:
        print('[DEBUG][Plugin Loader] Loading VapourSynth plugin: '+name, file=sys.stderr)
        try:
            core.std.LoadPlugin(join(path, 'vs', name))
        except vs.Error as e:
            print(f'[DEBUG][Plugin Loader] Load {name} failed with error: '+str(e), file=sys.stderr)
    for name in info['avsfilters']:
        print('[DEBUG][Plugin Loader] Loading AviSynth plugin: '+name, file=sys.stderr)
        core.avs.LoadPlugin(join(path, 'avs', name))
