import vapoursynth as vs

from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError

format_limits = ['HP_YUV420P8L',
                 'HP_YUV420P8F',
                 'HP_YUV420P10L',
                 'HP_YUV420P10F',
                 
                 'GRAY8',
                 'GRAY16',
                 'GRAYH',
                 'GRAYS',
                 
                 'YUV420P8',
                 'YUV422P8',
                 'YUV444P8',
                 'YUV410P8',
                 'YUV411P8',
                 'YUV440P8',
                 
                 'YUV420P9',
                 'YUV422P9',
                 'YUV444P9',
                 
                 'YUV420P10',
                 'YUV422P10',
                 'YUV444P10',
                 
                 'YUV420P12',
                 'YUV422P12',
                 'YUV444P12',
                 
                 'YUV420P14',
                 'YUV422P14',
                 'YUV444P14',
                 
                 'YUV420P16',
                 'YUV422P16',
                 'YUV444P16',
                 
                 'YUV444PH',
                 'YUV444PS',
                 
                 'RGB24',
                 'RGB27',
                 'RGB30',
                 'RGB48',
                 
                 'RGBH',
                 'RGBS',
                 
                 'COMPATBGR32',
                 'COMPATYUY2']


class Format:
    def __init__(self, _, format):
        self.format = str(format)
        if format not in format_limits:
            message = 'Format: %r method not found (supports %s)' % (
                format,
                ', '.join(format_limits), )
            raise ConfigureError(message)

    def __call__(self, core, clip):
        if self.format == 'HP_YUV420P8L':
            clip = mvf.ToYUV(clip, css="420", full=True)
            clip = mvf.Depth(clip, depth=8, fulls=True, fulld=False, dither=3)
        elif self.format == 'HP_YUV420P8F':
            clip = mvf.ToYUV(clip, css="420", full=True)
            clip = mvf.Depth(clip, depth=8, fulls=True, fulld=True, dither=3)
        elif self.format == 'HP_YUV420P10L':
            clip = mvf.ToYUV(clip, css="420", full=True)
            clip = mvf.Depth(clip, depth=10, fulls=True, fulld=False, dither=3)
        elif self.format == 'HP_YUV420P10F':
            clip = mvf.ToYUV(clip, css="420", full=True)
            clip = mvf.Depth(clip, depth=10, fulls=True, fulld=True, dither=3)
        else:
            clip = core.resize.Bicubic(clip, format=getattr(vs, self.format))
        return clip
