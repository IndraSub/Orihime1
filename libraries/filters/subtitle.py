import time
import vapoursynth as vs
from vapoursynth_tools import mvsfunc

from .utils import SimpleFilter, get_working_directory, merge_clips


@SimpleFilter
def VSFilterMod(core, clip, configure):
    subtitle = configure['source']['subtitle']
    file = get_working_directory(subtitle['filename'])
    clip = core.fmtc.resample(clip, css="420", fulls=True)
    return core.vsfm.TextSubMod(clip, file)


@SimpleFilter
def ASS(core, clip, configure):
    subtitle = configure['source']['subtitle']
    file = get_working_directory(subtitle['filename'])
    clip = core.fmtc.resample(clip, css="420", fulls=True)
    return core.vsfm.TextSubMod(clip, file)


@SimpleFilter
def InfoText(core, clip, configure):
    subtitle = configure['source']['subtitle']
    texts = subtitle['texts']
    clip = core.fmtc.resample(clip, css="420", fulls=True)
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))
    framenum = str(clip.num_frames)
    if len(texts):
        replaced = [
            core.text.Text(clip[idx], text.format(date=date, framenum=framenum, **configure))
            for idx, text in enumerate(texts)
        ]
        replaced.append(core.std.Trim(clip, len(texts)))
        return merge_clips(replaced)
    return clip
