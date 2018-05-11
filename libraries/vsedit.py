import base64
import json
import os
import sys
import time
import json

script_path = os.path.realpath(__file__)
script_directory = os.path.dirname(script_path)
root_directory = os.path.abspath(os.path.join(script_directory, '..'))

sys.path.append(os.path.join(root_directory, 'libraries'))
if sys.platform == 'linux':
    sys.path.append(os.path.join(root_directory, 'bin', 'linux', 'lib', 'python'))
else:
    sys.path.append(os.path.join(root_directory, 'bin', 'windows', 'lib', 'python'))

import yaml
import vapoursynth

from filters.utils import ConfigureError

configure = yaml.load('''
project:
  performance:
    vs_threads: 4
    vs_max_cache_size: 8192
  flow:
    # your filter confs here
source:
  filename: # source file here
  # other source confs here
''')

os.environ['TDINFO'] = json.dumps(yaml.load('''
vsfilters:
  # path to your vs filters here
avsfilters:
  # path to your avs filters here
'''))

def make_tasks(configure):
    import filters

    flow = configure['project']['flow']
    tasks = []
    for step in flow:
        if type(step) is str:
            step = {step: {}}
        if len(step) != 1:
            raise ConfigureError('Tasks: Less/More than one config in a single step, forget \'-\' ?')
        filter_name = list(step)[0]
        if not hasattr(filters, filter_name):
            raise ConfigureError('Tasks: Filter \'{}\' not found'.format(filter_name))
        filter_conf = step[filter_name]
        print(f'[Debug][Tasks] Add filter: {filter_name}', file=sys.stderr)
        if type(filter_conf) is list:
            tasks.append(getattr(filters, filter_name)(configure, *filter_conf))
        elif type(filter_conf) is dict:
            tasks.append(getattr(filters, filter_name)(configure, **filter_conf))
        else:
            tasks.append(getattr(filters, filter_name)(configure, filter_conf))
    return tasks

def main():
    from filters.plugins import load_plugins
    
    performance = configure['project']['performance']

    core = vapoursynth.get_core(threads=performance['vs_threads'])
    core.max_cache_size = performance['vs_max_cache_size']

    load_plugins(core)

    clip = None
    for task in make_tasks(configure):
        clip = task(core, clip)
    print('[DEBUG][Core] Output clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
    video = core.resize.Point(clip, matrix_in_s="709")
    video.set_output()


if __name__ == '__vapoursynth__':
    main()
