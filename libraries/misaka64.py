import base64
import json
import os
import sys
import time
import json

import vapoursynth

from filters.utils import ConfigureError

def make_tasks(configure):
    import filters

    flow = configure['project']['flow']
    tasks = []
    for step in flow:
        if type(step) is str:
            step = {step: {}}
        if len(step) != 1:
            raise ConfigureError('Process Flow: Less/More than one config in a single step, forget \'-\' ?')
        filter_name = list(step)[0]
        if not hasattr(filters, filter_name):
            raise ConfigureError('Process Flow: Filter \'{}\' not found'.format(filter_name))
        filter_conf = step[filter_name]
        print(f'TreeDiagram [Process Flow] Add External filter: {filter_name}', file=sys.stderr)
        if type(filter_conf) is list:
            tasks.append(getattr(filters, filter_name)(configure, *filter_conf))
        elif type(filter_conf) is dict:
            tasks.append(getattr(filters, filter_name)(configure, **filter_conf))
        else:
            tasks.append(getattr(filters, filter_name)(configure, filter_conf))
    return tasks

def main():
    from filters.utils import load_info
    from filters.plugins import load_plugins

    environment = load_info()
    configure = environment['content']
    performance = configure['project']['performance']

    core = vapoursynth.get_core(threads=performance['vs_threads'])
    core.max_cache_size = performance['vs_max_cache_size']

    load_plugins(core)

    clip = None
    for task in make_tasks(configure):
        clip = task(core, clip)
    print('TreeDiagram [Core] Output clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
    file = open(os.path.join(environment['temporary'], 'clipinfo.json'), 'w')
    clipinfo = {
        "format": clip.format.name,
        "resolution": [clip.width, clip.height],
        "frames": clip.num_frames,
        "fps": [clip.fps.numerator, clip.fps.denominator],
        "flags": clip.flags
    }
    data = json.dumps(clipinfo)
    file.write(data)
    file.close()
    video = core.resize.Point(clip, matrix_in_s="709")
    video.set_output()


if __name__ == '__vapoursynth__':
    main()
