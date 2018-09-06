import sys

from os.path import join, dirname
import os
import platform
import vapoursynth as vs
import json

info = json.loads(os.environ['TDINFO'])

def load_plugins(core):
    for path in info['vsfilters']:
        name = os.path.basename(path)
        print('TreeDiagram [Plugin Loader] Loading External VapourSynth plugin: '+name, file=sys.stderr)
        try:
            core.std.LoadPlugin(path)
        except vs.Error as e:
            print(f'TreeDiagram [Plugin Loader] Load {name} failed with error: '+str(e), file=sys.stderr)
    for path in info['avsfilters']:
        name = os.path.basename(path)
        print('TreeDiagram [Plugin Loader] Loading External AviSynth plugin: '+name, file=sys.stderr)
        try:
            core.avs.LoadPlugin(path)
        except vs.Error as e:
            print(f'TreeDiagram [Plugin Loader] Load {name} failed with error: '+str(e), file=sys.stderr)
