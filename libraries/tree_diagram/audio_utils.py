#!/usr/bin/env python3

import subprocess
import xml.etree.ElementTree as ET
import collections
import os

from . import info
from .kit import assertFileWithExit
from .process_utils import invokePipeline
from .audio_filters import *

def getSourceInfo(source: str) -> int:
    xmlstr = subprocess.run([info.MEDIAINFO, '--Output=XML', source], stdout=subprocess.PIPE).stdout.decode('utf8')
    xml = ET.fromstring(xmlstr)
    vdelay = None
    adelay = None
    fps = None
    for track in xml.iter('{https://mediaarea.net/mediainfo}track'):
        if track.attrib['type'] == 'Video':
            d = track.find('{https://mediaarea.net/mediainfo}Delay')
            if d is not None:
                vdelay = float(d.text)
            fps = float(track.find('{https://mediaarea.net/mediainfo}FrameRate').text)
        elif track.attrib['type'] == 'Audio':
            d = track.find('{https://mediaarea.net/mediainfo}Delay')
            if d is not None:
                adelay = float(d.text)
    print(f'TreeDiagram [Audio Utils] FrameRate: {fps} fps')
    if vdelay is None:
        print('TreeDiagram [Audio Utils] AudioDelay: video delay not found, assume it to 0.')
        vdelay = 0
    if adelay is None:
        print('TreeDiagram [Audio Utils] AudioDelay: audio delay not found, assume it to 0.')
        adelay = 0
    if fps is None:
        print('TreeDiagram [Audio Utils] AudioDelay: fps not found, assume it to 24000/1001.')
        fps = 24000/1001
    delay = int((adelay - vdelay) * 1000)
    print(f'TreeDiagram [Audio Utils] AudioDelay: {delay} ms')
    return fps, delay

def extractAudio(source: str, extractedAudio: str) -> None:
    print('TreeDiagram [Audio Utils] Extracting audio file, this may take a while on long videos...')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', source, '-vn', '-acodec', 'pcm_s16be', '-f', 'aiff', extractedAudio]
    ])
    assertFileWithExit(extractedAudio)

def encodeAudio(trimmedAudio: str, encodedAudio: str) -> None:
    print('TreeDiagram [Audio Utils] Recoding audio data to AAC format with QAAC')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', trimmedAudio, '-f', 'wav', '-vn', '-'],
        [info.QAAC, '--tvbr', '127', '--quality', '2', '--ignorelength', '-o', encodedAudio, '-'],
    ])
    assertFileWithExit(encodedAudio)

def trimAudio(source: str, extractedAudio: str, trimmedAudio: str, frames=None) -> None:
    fps, delay = getSourceInfo(source)
    print('TreeDiagram [Audio Utils] Trimming audio file...')
    src = AudioAiffSource(extractedAudio)
    params = src.getparams()
    out = None
    if frames:
        for first, last in frames:
            first_samp = round(first * params.framerate / fps - delay * params.framerate / 1000)
            last_samp = round((last + 1) * params.framerate / fps - delay * params.framerate / 1000)
            if out is None:
                out = AudioTrim(src, first_samp, last_samp)
            else:
                out = AudioConcat(out, AudioTrim(src, first_samp, last_samp))
    else:
        delay_samp = round(delay * params.framerate / 1000)
        if delay_samp > 0:
            out = AudioConcat(Silence(wave_params(**{**params._asdict(), 'nframes': delay_samp})), src)
        else:
            out = AudioTrim(src, -delay_samp)
    out = AudioOutput(out, trimmedAudio, format='wav')
    nchannels, sampwidth, framerate, nframes, comptype, compname = out.getparams()
    print(f'TreeDiagram [Audio Utils] Audio output: {nchannels} channel(s), {framerate} Hz, {nframes} frames, {nframes / framerate :.3f} s')
    out.run()
    assertFileWithExit(trimmedAudio)

def mergeAndTrimAudio(numAudio: int, trimmedAudio: str, frames=None) -> None:
    src = AudioAiffSource(os.path.join(info.temporary, '0.aif'))
    for i in range(1, numAudio):
        src = AudioConcat(wav, AudioAiffSource(os.path.join(info.temporary, f'{i}.aif')))
    params = src.getparams()
    out = None
    if frames:
        for first, last in frames:
            first_samp = round(first * params.framerate / fps - delay * params.framerate / 1000)
            last_samp = round((last + 1) * params.framerate / fps - delay * params.framerate / 1000)
            if out is None:
                out = AudioTrim(src, first_samp, last_samp)
            else:
                out = AudioConcat(out, AudioTrim(src, first_samp, last_samp))
    else:
        out = src
    out = AudioOutput(out, trimmedAudio, format='wav')
    out.run()
    assertFileWithExit(trimmedAudio)
