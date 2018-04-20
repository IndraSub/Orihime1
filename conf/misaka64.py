import base64
import json
import os
import sys
import time

import vapoursynth

sys.path.insert(0, os.path.realpath('.'))
sys.path.append(os.path.realpath('./libraries/yaml.zip'))
sys.path.append(os.path.realpath('./libraries/vapoursynth_tools.zip'))


def load_working_content():
    import yaml
    from filters.utils import get_working_directory

    working = get_working_directory(current_working.decode())
    working = yaml.load(open(working).read())

    working['project'] = get_working_directory(working['project'])
    working['project'] = yaml.load_all(open(working['project']).read())
    working['project'] = next(project for project in working['project']
                              if project['quality'] == working['quality'])
    return working


def make_tasks(configure):
    from filters import (Dering, EdgeRefine, LineClearness, LineSharp, Source,
                         makeDeband, makeCropBefore, makeCropAfter,
                         makeDelogo, makeDenoise, makeUpscale,
                         makeUnsharpMasking, makeEnabled, makeFormat, makeMCFI,
                         makePostProcess, makeResolution, makeSubtitle, makeTrimFrames, makeTrimAudio)

    source = configure['source']
    flow = configure['project']['flow']
    filter_conf = configure['project']['filter_configure']
    trim_frames = source.get('trim_frames', [])
    makeArgs = lambda name: (
        flow.get(name, False),
        filter_conf.get(name, {}), )
    return (
        Source(source['filename'], *makeArgs('Source')),
        makeTrimAudio(flow.get('TrimFrames', False), temporary.decode(), ffmpeg.decode(), mediainfo.decode(), source['filename'], trim_frames),
        makeTrimFrames(flow.get('TrimFrames', False), trim_frames),
        makePostProcess(*makeArgs('PostProcess')),
        makeCropBefore(*makeArgs('CropBefore')),
        makeDelogo(trim_frames, *makeArgs('Delogo')),
        makeDenoise(*makeArgs('Denoise')),
        makeUpscale(*makeArgs('Upscale')),
        makeUnsharpMasking(*makeArgs('UnsharpMasking')),
        makeEnabled(flow.get('Dering', False), Dering),
        makeEnabled(flow.get('LineClearness', False), LineClearness),
        makeEnabled(flow.get('EdgeRefine', False), EdgeRefine),
        makeEnabled(flow.get('LineSharp', False), LineSharp),
        makeMCFI(*makeArgs('MCFI')),
        makeCropAfter(*makeArgs('CropAfter')),
        makeResolution(*makeArgs('Resolution')),
        makeSubtitle(source.get('subtitle')),
        makeDeband(flow.get('Deband', False)),
        makeFormat(flow.get('Format', False)), )


def main():
    from filters.plugins import load_plugins
    
    configure = load_working_content()
    performance = configure['project']['performance']

    core = vapoursynth.get_core(threads=performance['vs_threads'])
    core.max_cache_size = performance['vs_max_cache_size']

    load_plugins(core)

    clip = None
    for task in make_tasks(configure):
        if task is None:
            continue
        clip = task(core, clip)
    print('[DEBUG][Core] Output clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
    video = core.resize.Point(clip, matrix_in_s="709")
    video.set_output()


if __name__ == '__vapoursynth__':
    main()
