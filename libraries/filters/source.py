import sys

from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError, get_working_directory

methods = {
    'LWLibavSource': lambda core, source: core.lsmas.LWLibavSource(source),
    'LSMASHVideoSource': lambda core, source: core.lsmas.LSMASHVideoSource(source),
    'ffms2': lambda core, source: core.ffms2.Source(source),
    'AVISource': lambda core, source: core.avisource.AVISource(source)
}


class Source:
    def __init__(self, file, method, params):
        if method not in methods:
            message = 'Source: %r source loader not found (supports %s)' % (
                method,
                ', '.join(methods.keys()), )
            raise ConfigureError(message)
        if params['range'] == 'full':
            self.range = True
        elif params['range'] == 'limited':
            self.range = False
        else:
            message = 'Source: invalid range value: {}'.format(range)
            raise ConfigureError(message)
        self.method = method
        self.file = get_working_directory(file)

    def __call__(self, core, clip):
        clip = methods[self.method](core, self.file)
        print('[DEBUG][Source] Input clip info: format:'+clip.format.name+' width:'+str(clip.width)+' height:'+str(clip.height)+' num_frames:'+str(clip.num_frames)+' fps:'+str(clip.fps)+' flags:'+str(clip.flags), file=sys.stderr)
        clip = core.fmtc.resample(clip, css="420")
        clip = mvf.Depth(clip, depth=8, fulls=self.range, fulld=True, dither=3)
        return clip
