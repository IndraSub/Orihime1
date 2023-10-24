import vapoursynth as vs

from vapoursynth_tools import mvsfunc as mvf

from .utils import ConfigureError

format_limits = [
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
                'COMPATYUY2',
                
                'Resample_YUV420P16_Full',
                'Resample_YUV420P16_Limited',
                'Resample_YUV444P16_Full',
                'Resample_YUV444P16_Limited',
                'Matrix_BT709_Full',
                'Matrix_BT709_Limited',
                'Depth_8_Full',
                'Depth_8_Limited',
                'Depth_10_Full',
                'Depth_10_Limited',
                'Depth_12_Full',
                'Depth_12_Limited',
                'Depth_16_Full',
                'Depth_16_Limited',
                'Range_Full',
                'Range_Limited',
                ]


class Format:
    def __init__(self, _, format):
        self.format = str(format)
        if format not in format_limits:
            message = 'Format: %r method not found (supports %s)' % (
                format,
                ', '.join(format_limits), )
            raise ConfigureError(message)

    def __call__(self, core, clip):
        if self.format == 'Resample_YUV420P16_Full':
            clip = core.fmtc.resample(clip, css="420", csp=vs.YUV420P16, fulls=True)
        elif self.format == 'Resample_YUV420P16_Limited':
            clip = core.fmtc.resample(clip, css="420", csp=vs.YUV420P16, fulls=False)
        elif self.format == 'Resample_YUV444P16_Full':
            clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444P16, fulls=True)
        elif self.format == 'Resample_YUV444P16_Limited':
            clip = core.fmtc.resample(clip, css="444", csp=vs.YUV444P16, fulls=False)
        elif self.format == 'Matrix_BT709_Full':
            clip = core.fmtc.matrix(clip, mats="601", matd="709", fulls=True)
        elif self.format == 'Matrix_BT709_Limited':
            clip = core.fmtc.matrix(clip, mats="601", matd="709", fulls=False)
        elif self.format == 'Depth_8_Full':
            clip = mvf.Depth(clip, depth=8, fulls=True, fulld=True, dither=3)
        elif self.format == 'Depth_8_Limited':
            clip = mvf.Depth(clip, depth=8, fulls=False, fulld=False, dither=3)
        elif self.format == 'Depth_10_Full':
            clip = mvf.Depth(clip, depth=10, fulls=True, fulld=True, dither=3)
        elif self.format == 'Depth_10_Limited':
            clip = mvf.Depth(clip, depth=10, fulls=False, fulld=False, dither=3)
        elif self.format == 'Depth_12_Full':
            clip = mvf.Depth(clip, depth=12, fulls=True, fulld=True, dither=3)
        elif self.format == 'Depth_12_Limited':
            clip = mvf.Depth(clip, depth=12, fulls=False, fulld=False, dither=3)
        elif self.format == 'Depth_16_Full':
            clip = mvf.Depth(clip, depth=16, fulls=True, fulld=True, dither=3)
        elif self.format == 'Depth_16_Limited':
            clip = mvf.Depth(clip, depth=16, fulls=False, fulld=False, dither=3)
        elif self.format == 'Range_Full':
            clip = core.fmtc.bitdepth(clip, fulls=False, fulld=True)
        elif self.format == 'Range_Limited':
            clip = core.fmtc.bitdepth(clip, fulls=True, fulld=False)
        else:
            clip = core.resize.Bicubic(clip, format=getattr(vs, self.format))
        return clip
