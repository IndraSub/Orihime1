from .crop_after import CropAfter
from .crop_before import CropBefore
from .deband import Deband
from .delogo import Delogo
from .denoise import Denoise
from .dering import Dering
from .edge_refine import EdgeRefine
from .line_clearness import LineClearness
from .line_sharp import LineSharp
from .format import Format
from .mcfi import MCFI
from .post_process import PostProcess
from .resolution import Resolution
from .source import Source
from .subtitle import Subtitle
from .trim_frames import TrimFrames, TrimAudio
from .unsharp_masking import UnsharpMasking
from .upscale import Upscale


def makeTrimFrames(enabled, trim_frames):
    if enabled is False:
        return
    return TrimFrames(trim_frames)

def makeTrimAudio(enabled, temporary, ffmpeg, file, trim_frames):
    return TrimAudio(enabled, temporary, ffmpeg, file, trim_frames)

def makePostProcess(method, configure):
    if method is False:
        return
    return PostProcess(method, configure.get(method, {}))


def makeCropBefore(enabled, configure):
    if enabled is False:
        return
    return CropBefore(
        configure.get('width', 1280),
        configure.get('height', 720), )


def makeCropAfter(enabled, configure):
    if enabled is False:
        return
    return CropAfter(
        configure.get('top', 0),
        configure.get('bottom', 0), )


def makeDelogo(trim_frames, enabled, configure):
    if enabled is False:
        return
    return Delogo(logo_file=configure.get('logo_file'), frames=trim_frames, )


def makeDenoise(method, configure):
    if method is False:
        return
    return Denoise(method, configure.get(method, {}))


def makeUpscale(method, configure):
    if method is False:
        return
    return Upscale(method, configure.get(method, {}))


def makeUnsharpMasking(enabled, configure):
    if enabled is False:
        return
    return UnsharpMasking(
        configure.get('strength', 2.0),
        configure.get('final', 0.1), )


def makeDeband(method):
    if method is False:
        return
    return Deband(method)


def makeMCFI(method, configure):
    if method is False:
        return
    if method is True:
        method = 'SVP'
    return MCFI(method, configure.get(method, {}))


def makeResolution(enabled, configure):
    if enabled is False:
        return
    return Resolution(
        configure.get('width', 1280),
        configure.get('height', 720), )


def makeSubtitle(subtitle):
    if subtitle is None:
        return
    return Subtitle(subtitle.get('filename'), subtitle.get('texts', []))


def makeFormat(format):
    if format is False:
        return
    return Format(format)


def makeEnabled(enabled, handler):
    if enabled is False:
        return
    return handler()
