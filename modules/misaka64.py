import json
import os
import sys
import vapoursynth

sys.path.append(".")

# pylint: disable=wrong-import-position
from filters.plugins import load_plugins
from filters.utils import load_info
from filters.utils import ConfigureError

def make_tasks(configure):
    # pylint: disable=import-outside-toplevel
    import filters

    flow = configure['project']['flow']
    tasks = []
    for step in flow:
        if isinstance(step, str):
            step = {step: {}}
        if len(step) != 1:
            raise ConfigureError('Core: Less/More than one config in a single step, forgot \'-\' ?')
        filter_name = list(step)[0]
        if not hasattr(filters, filter_name):
            raise ConfigureError(f'Core: Filter {filter_name} not found')
        filter_conf = step[filter_name]
        print(f'Core: Add External filter: {filter_name}', file=sys.stderr)
        if isinstance(filter_conf, list):
            tasks.append(getattr(filters, filter_name)(configure, *filter_conf))
        elif isinstance(filter_conf, dict):
            tasks.append(getattr(filters, filter_name)(configure, **filter_conf))
        else:
            tasks.append(getattr(filters, filter_name)(configure, filter_conf))
    return tasks

def main():

    environment = load_info()
    configure = environment['content']
    performance = configure['project']['performance']

    core = vapoursynth.core
    core.num_threads = performance['vs_threads']
    core.max_cache_size = performance['vs_max_cache_size']

    load_plugins(core)

    clip = None
    for task in make_tasks(configure):
        clip = task(core, clip)
    print('Core: Output clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps), file=sys.stderr)
    file = open(os.path.join(environment['temporary'], 'clipinfo.json'), 'w', encoding='utf-8')
    clipinfo = {
        "format": clip.format.name,
        "resolution": [clip.width, clip.height],
        "frames": clip.num_frames,
        "fps": [clip.fps.numerator, clip.fps.denominator]
    }
    data = json.dumps(clipinfo)
    file.write(data)
    file.close()
    video = core.resize.Point(clip, matrix_in_s="709")
    video.set_output()


if __name__ == '__vapoursynth__':
    main()
