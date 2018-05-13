#!/usr/bin/env python3

import subprocess
import xml.etree.ElementTree as ET
import wave, aifc
import collections

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
        [info.FFMPEG, '-hide_banner', '-i', source, '-vn', '-acodec', 'pcm_s16le', '-f', 'aiff', extractedAudio]
    ])
    assertFileWithExit(extractedAudio)

def encodeAudio(trimmedAudio: str, encodedAudio: str) -> None:
    print('Recoding audio data to AAC format with QAAC')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', trimmedAudio, '-f', 'wav', '-vn', '-'],
        [info.QAAC, '--tvbr', '127', '--quality', '2', '--ignorelength', '-o', encodedAudio, '-'],
    ])
    assertFileWithExit(encodedAudio)

class AudioProcessError(Exception):
    pass

wave_params = collections.namedtuple('wave_params',
        ['nchannels', 'sampwidth', 'framerate', 'nframes', 'comptype', 'compname'])

class AudioWavSource:
    def __init__(self, wavfile):
        self.wav = wave.open(wavfile, 'rb')
    def getparams(self):
        return self.wav.getparams()
    def readframes(self, start, n):
        self.wav.setpos(start)
        return self.wav.readframes(n)
    def __del__(self):
        self.wav.close()

class AudioAiffSource:
    def __init__(self, wavfile):
        self.wav = aifc.open(wavfile, 'rb')
    def getparams(self):
        return self.wav.getparams()
    def readframes(self, start, n):
        self.wav.setpos(start)
        return self.wav.readframes(n)
    def __del__(self):
        self.wav.close()

class AudioTrim:
    def __init__(self, wav, start=0, end=None):
        if end is None:
            end = wav.getparams().nframes
        params = wav.getparams()
        if start < 0 or end < start or params.nframes < end:
            raise AudioProcessError('Bad trim parameters')
        self.wav = wav
        self.start = start
        self.end = end
        self.params = wave_params(**{**params._asdict(), 'nframes': self.end - self.start})
    def getparams(self):
        return self.params
    def readframes(self, start, n):
        realstart = self.start + start
        if realstart + n > self.end:
            n = self.end - realstart
        return self.wav.readframes(realstart, n)

class AudioConcat:
    def __init__(self, wav1, wav2):
        self.wav1 = wav1
        self.wav2 = wav2
        params1 = wav1.getparams()
        params2 = wav2.getparams()
        if params1.nchannels != params2.nchannels or params1.sampwidth != params2.sampwidth or params1.framerate != params2.framerate:
            raise AudioProcessError('Audio parameters mismatch')
        self.nframes1 = params1.nframes
        self.nframes2 = params2.nframes
        self.params = wave_params(**{**params1._asdict(), 'nframes': params1.nframes + params2.nframes})
    def getparams(self):
        return self.params
    def readframes(self, start, n):
        seg = b''
        if start < self.nframes1:
            read1 = n
            if self.nframes1 - start < n:
                read1 = self.nframes1 - start
            seg += self.wav1.readframes(start, read1)
            start += read1
            n -= read1
        if n > 0:
            seg += self.wav2.readframes(start - self.nframes1, n)
        return seg

class Silence:
    def __init__(self, params):
        self.params = params
    def getparams(self):
        return self.params
    def readframes(self, start, n):
        if start + n > self.params.nframes:
            n = self.params.nframes - start
        return b'\x00' * (self.params.nchannels * self.params.sampwidth * n)

def trimAudio(source: str, extractedAudio: str, trimmedAudio: str, frames=None) -> None:
    fps, delay = getSourceInfo(source)
    print('Trimming audio file...')
    src = AudioAiffSource(extractedAudio)
    params = src.getparams()
    out = None
    if frames:
        for first, last in frames:
            first_samp = first * params.framerate / fps - delay * params.framerate / 1000
            last_samp = (last + 1) * params.framerate / fps - delay * params.framerate / 1000
            if out is None:
                out = AudioTrim(src, first_samp, last_samp)
            else:
                out = AudioConcat(out, AudioTrim(src, first_samp, last_samp))
    else:
        delay_samp = delay * params.framerate / 1000
        if delay_samp > 0:
            out = AudioConcat(Silence(wave_params(**{**params._asdict(), 'nframes': delay_samp})), src)
        else:
            out = AudioTrim(src, -delay_samp)
    outfile = wave.open(trimmedAudio, 'wb')
    outfile.setparams(out.getparams())
    outfile.writeframes(out.readframes(0, out.getparams().nframes))
    outfile.close()
    assertFileWithExit(trimmedAudio)
