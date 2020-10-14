#!/usr/bin/env python3

import subprocess
import xml.etree.ElementTree as ET
import os

from . import info
from .kit import assertFileWithExit
from .process_utils import invokePipeline
from .audio_filters import AudioWavSource, AudioAiffSource, AudioConcat, AudioTrim, AudioOutput, Silence, \
    wave_params

def getSourceInfo(source: str) -> int:
    xmlstr = subprocess.run([info.MEDIAINFO, '--Output=XML', source], stdout=subprocess.PIPE).stdout.decode('utf8')
    xml = ET.fromstring(xmlstr)
    vdelay = None
    adelay = None
    # for MediaInfo Linux version
    for track in xml.iter('{https://mediaarea.net/mediainfo}track'):
        if track.attrib['type'] == 'Video':
            d = track.find('{https://mediaarea.net/mediainfo}Delay')
            if d is not None:
                vdelay = float(d.text)
        elif track.attrib['type'] == 'Audio':
            d = track.find('{https://mediaarea.net/mediainfo}Delay')
            if d is not None:
                adelay = float(d.text)
    # for MediaInfo Windows version
    for track in xml.iter('track'):
        if track.attrib['type'] == 'Video':
            d = track.find('Delay')
            if d is not None:
                vdelay = float(d.text)
        elif track.attrib['type'] == 'Audio':
            d = track.find('Delay')
            if d is not None:
                adelay = float(d.text)
    if vdelay is None:
        print('TreeDiagram [Audio Utils] No video delay in stream meta, assume it to 0.')
        vdelay = 0
    if adelay is None:
        print('TreeDiagram [Audio Utils] No audio delay in stream meta, assume it to 0.')
        adelay = 0
    if info.content['source']['audio_delay']:
        delay = info.content['source']['audio_delay']
    else:
        delay = int((adelay - vdelay) * 1000)
    print(f'TreeDiagram [Audio Utils] Audio delay related to video: {delay} ms')
    return delay

def extractAudio(source: str, extractedAudio: str) -> None:
    print('TreeDiagram [Audio Utils] Extracting audio data, this may take a while on long videos...')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', source, '-vn', '-acodec', 'pcm_s16be', '-f', 'aiff', extractedAudio]
    ])
    assertFileWithExit(extractedAudio)

def encodeAudio(trimmedAudio: str, encodedAudio: str) -> None:
    print('TreeDiagram [Audio Utils] Encoding audio data to AAC format with QAAC')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', trimmedAudio, '-f', 'wav', '-vn', '-'],
        [info.QAAC, '--tvbr', '127', '--quality', '2', '--ignorelength', '-o', encodedAudio, '-'],
    ])
    assertFileWithExit(encodedAudio)

def trimAudio(source: str, extractedAudio: str, trimmedAudio: str, fps: list, frames=None) -> None:
    fps = fps[0] / fps[1]
    print(f'TreeDiagram [Audio Utils] Video stream framerate: {fps} fps')
    delay = getSourceInfo(source)
    print('TreeDiagram [Audio Utils] Trimming wave file...')
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

def mergeAndTrimAudio(numAudio: int, trimmedAudio: str, fps: list =None, frames=None) -> None:
    src = AudioAiffSource(os.path.join(info.temporary, '0.aif'))
    for i in range(1, numAudio):
        src = AudioConcat(src, AudioAiffSource(os.path.join(info.temporary, f'{i}.aif')))
    params = src.getparams()
    out = None
    if frames:
        fps = fps[0] / fps[1]
        delay = 0 # Note: any way to decide?
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
