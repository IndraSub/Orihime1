import sys

from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError, SimpleFilter, get_working_directory, merge_clips

def SourceFilter(filter_func):
    @SimpleFilter
    def source(core, _, configure, range):
        if range == 'full':
            range = True
        elif range == 'limited':
            range = False
        else:
            message = 'Source: invalid range value: {}'.format(range)
            raise ConfigureError(message)
        file = get_working_directory(configure['source']['filename'])
        clip = filter_func(core, file)
        print('TreeDiagram [Source] Input clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
        clip = core.fmtc.resample(clip, css="420")
        clip = mvf.Depth(clip, depth=8, fulls=range, fulld=False, dither=3)
        return clip
    return source

@SourceFilter
def LWLibavSource(core, source):
    return core.lsmas.LWLibavSource(source)

@SourceFilter
def LSMASHVideoSource(core, source):
    return core.lsmas.LSMASHVideoSource(source)

@SourceFilter
def FFmpegSource(core, source):
    return core.ffms2.Source(source, seekmode=0)

@SourceFilter
def AVISource(core, source):
    return core.avisource.AVISource(source)

@SimpleFilter
def MultiSource(core, clip, configure, source_filter, range):
    sf = None
    if source_filter == 'LWLibavSource':
        sf = core.lsmas.LWLibavSource
    elif source_filter == 'LSMASHVideoSource':
        sf = core.lsmas.LSMASHVideoSource
    elif source_filter == 'FFMS2Source':
        sf = core.ffms2.Source
    elif source_filter == 'AVISource':
        sf = core.avisource.AVISource
    else:
        raise ConfigureError(f'Source: Cannot find source filter: {source_filter}')
    clips = [sf(get_working_directory(filename)) for filename in configure['source']['filenames']]
    clip = merge_clips(clips)
    print('TreeDiagram [Source] Input clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
    clip = core.fmtc.resample(clip, css="420")
    clip = mvf.Depth(clip, depth=8, fulls=range, fulld=False, dither=3)
    return clip
