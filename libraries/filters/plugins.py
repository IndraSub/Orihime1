import sys

from os.path import join, dirname
import os
import platform
import vapoursynth as vs

## Windows
std_plugins_windows = (
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

avs_plugins_windows = (
    'TIVTC64.dll',  # TIVTC # This is an AviSynth filter
)

## Linux
std_plugins_linux = ()

## Linux with wine, appended
std_plugins_wine = ()

avs_plugins_wine = (
    'TIVTC64.dll',  # TIVTC # This is an AviSynth filter    
)

if platform.system() == 'Windows':
    std_plugins = std_plugins_windows
    avs_plugins = avs_plugins_windows
else:
    std_plugins = std_plugins_linux
    avs_plugins = ()
    if True:
        std_plugins = std_plugins + std_plugins_wine
        avs_plugins = avs_plugins + avs_plugins_wine

def load_plugins(core):
    path = join(dirname(__file__), '..', '..', 'bin', platform.system().lower(), 'filter_plugins')
    for name in std_plugins:
        print('[DEBUG][Plugin Loader] Loading VapourSynth plugin: '+name, file=sys.stderr)
        try:
            core.std.LoadPlugin(join(path, 'vs', name))
        except vs.Error as e:
            print(f'[DEBUG][Plugin Loader] Load {name} failed with error: '+str(e), file=sys.stderr)
    for name in avs_plugins:
        print('[DEBUG][Plugin Loader] Loading AviSynth plugin: '+name, file=sys.stderr)
        core.avs.LoadPlugin(join(path, 'avs', name))
