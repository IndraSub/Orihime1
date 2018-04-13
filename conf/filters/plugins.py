import sys

from os.path import join, dirname

avs_plugins = (
    'TIVTC64.dll',  # TIVTC # This is an AviSynth filter
)

std_plugins = (
    'BM3D.dll',  # BM3D
    'CTMF.dll',  # CTMF # Required by HQDeringmod
    'DFTTest.dll',  # DFTTest # Required by TEdge
    'ffms2.dll',  # FFmpegSource2 Source
    'flash3kyuu_deband.dll',  # f3kdb
    'fmtconv.dll',  # fmtconv # Required by QTGMC
    'libAWarpSharp2.dll',  # AWarpSharp2
    'libDelogo.dll',  # delogo
    'libMVTools.dll',  # MVTools
    'libNNEDI3.dll',  # nnedi3 # Required by QTGMC
    'libsangnom.dll',  # SangNom # Required by LineClearness
    'libTemporalSoften.dll',  # TemporalSoften # Required by QTGMC
    'SceneChange.dll',  # SceneChange # Required by QTGMC
    'SVPFlow1.dll',  # SVPflow1
    'SVPFlow2.dll',  # SVPflow2
    'TemporalSoften.dll',  # TemporalSoften # Required by SceneChange
    'VagueDenoiser.dll', # VagueDenoiser
    'vs_it.dll', # Inverse Telecine
    'VSFFT3DFilter.dll',  # FFT3DFilter # Required by QTGMC
    'VSFilterMod.dll',  # VSFilterMod
    'VSLSMASHSource.dll',  # L-SMASH Source
    join('waifu2x-caffe', 'Waifu2x-caffe.dll'),  # Waifu2x-caffe
    join('waifu2x-w2xc', 'Waifu2x-w2xc.dll'),  # Waifu2x-w2xc
)


def load_plugins(core):
    path = join(dirname(__file__), '..', '..', 'bin', 'filter_plugins')
    for name in avs_plugins:
        print('[DEBUG][Plugin Loader] Loading AviSynth plugin: '+name, file=sys.stderr)
        core.avs.LoadPlugin(join(path, 'avs', name))
    for name in std_plugins:
        print('[DEBUG][Plugin Loader] Loading VapourSynth plugin: '+name, file=sys.stderr)
        core.std.LoadPlugin(join(path, 'vs', name))
