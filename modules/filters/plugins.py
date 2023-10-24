import sys
import os
import json
import vapoursynth as vs

info = json.loads(os.environ['TDINFO'])

def load_plugins(core):
    for path in info['vsfilters']:
        name = os.path.basename(path)
        print('PluginLoader: Loading External VapourSynth plugin: '+name, file=sys.stderr)
        try:
            core.std.LoadPlugin(path)
        except vs.Error as e:
            print(f'PluginLoader: Load {name} failed with error: '+str(e), file=sys.stderr)
    for path in info['avsfilters']:
        name = os.path.basename(path)
        print('PluginLoader: Loading External AviSynth plugin: '+name, file=sys.stderr)
        try:
            core.avs.LoadPlugin(path)
        except vs.Error as e:
            print(f'PluginLoader: Load {name} failed with error: '+str(e), file=sys.stderr)
