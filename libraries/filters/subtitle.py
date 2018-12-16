import time
import vapoursynth as vs

from vapoursynth_tools import havsfunc as haf
from vapoursynth_tools import mvsfunc as mvf

from .utils import SimpleFilter, ConfigureError, get_working_directory, merge_clips


@SimpleFilter
def VSFilterMod(core, clip, configure):
    subtitle = configure['source']['subtitle']
    file = get_working_directory(subtitle['filename'])
    clip = core.fmtc.resample(clip, css="420", fulls=True)
    return core.vsfm.TextSubMod(clip, file)


@SimpleFilter
def Subtext(core, clip, configure):
    subtitle = configure['source']['subtitle']
    file = get_working_directory(subtitle['filename'])
    clip = mvf.ToYUV(clip, css="444", full=False)
    clip = mvf.Depth(clip, depth=16, fulls=True, fulld=True, dither=3)
    rendered = core.sub.TextFile(clip, file, blend=False)
    subtext = []
    for index in range(2):
        yuv = mvf.ToYUV(rendered[index], css="444", full=False)
        subtext.append(mvf.Depth(yuv, depth=16, fulls=True, fulld=True, dither=3))
    return core.std.MaskedMerge(clipa=clip, clipb=subtext[0], mask=subtext[1])


@SimpleFilter
def InfoText(core, clip, configure):
    subtitle = configure['source']['subtitle']
    texts = subtitle['texts']
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))
    framenum = str(clip.num_frames)
    clip = core.fmtc.resample(clip, css="420", fulls=True)
    if len(texts):
        replaced = [
            core.text.Text(clip[idx], text.format(date=date, framenum=framenum, **configure))
            for idx, text in enumerate(texts)
        ]
        replaced.append(core.std.Trim(clip, len(texts)))
        return merge_clips(replaced)
    return clip
