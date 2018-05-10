import sys

from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError, SimpleFilter, get_working_directory

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
        print('[DEBUG][Source] Input clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
        clip = core.fmtc.resample(clip, css="420")
        clip = mvf.Depth(clip, depth=8, fulls=range, fulld=True, dither=3)
        return clip
    return source

@SourceFilter
def LWLibavSource(core, source):
    return core.lsmas.LWLibavSource(source)

@SourceFilter
def LSMASHVideoSource(core, source):
    return core.lsmas.LSMASHVideoSource(source)

@SourceFilter
def FFMS2Source(core, source):
    return core.ffms2.Source(source)

@SourceFilter
def AVISource(core, source):
    return core.avisource.AVISource(source)

