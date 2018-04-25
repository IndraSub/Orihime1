#!/usr/bin/env python3

import subprocess
import xml.etree.ElementTree as ET
import pydub

from . import info
from .kit import assertFileWithExit
from .process_utils import invokePipeline

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
    print(f'FrameRate: {fps} fps')
    if vdelay is None:
        print('AudioDelay: video delay not found')
        vdelay = 0
    if adelay is None:
        print('AudioDelay: audio delay not found')
        return 0
    delay = int((adelay - vdelay) * 1000)
    print(f'AudioDelay: {delay} ms')
    return fps, delay

def extractAudio(source: str, extractedAudio: str) -> None:
    print('Extracting audio file, this may take a while on long videos...')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', source, '-vn', '-acodec', 'pcm_s16le', '-f', 'wav', extractedAudio]
    ])
    assertFileWithExit(extractedAudio)

def trimAudio(source: str, extractedAudio: str, trimmedAudio: str, frames=None) -> None:
    fps, delay = getSourceInfo(source)
    print('Trimming audio file...')
    src = pydub.AudioSegment.from_wav(extractedAudio)
    segments = []
    if frames:
        for first, last in frames:
            first_ms = first * 1000 / fps - delay
            last_ms = (last + 1) * 1000 / fps - delay
            segments.append(src[first_ms:last_ms])
    else:
        segments.append(src[-delay if delay < 0 else 0:]) # NOTE: prepending silence?
    out = segments[0]
    for item in segments[1:]:
        out += item
    out.export(trimmedAudio, format='wav')
    assertFileWithExit(trimmedAudio)

def encodeAudio(trimmedAudio: str, encodedAudio: str) -> None:
    print('Recoding audio data to AAC format with QAAC')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', trimmedAudio, '-f', 'wav', '-vn', '-'],
        [info.QAAC, '--tvbr', '127', '--quality', '2', '--ignorelength', '-o', encodedAudio, '-'],
    ])
    assertFileWithExit(encodedAudio)
