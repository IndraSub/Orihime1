#!/usr/bin/env python3

import collections, wave, aifc

class AudioProcessError(Exception):
    pass

wave_params = collections.namedtuple('wave_params',
        ['nchannels', 'sampwidth', 'framerate', 'nframes', 'comptype', 'compname'])

def endian_conv(buf, width):
    swapped = bytearray(len(buf))
    for i in range(0, width):
        swapped[width-1-i::width] = buf[i::width]
    return bytes(swapped)

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
        width = self.getparams.sampwidth
        return endian_conv(self.wav.readframes(n), width)
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

class AudioOutput:
    def __init__(self, wav, filename, format='aif'):
        self.input = wav
        if format == 'aif':
            self.output = aifc.open(filename, 'wb')
            self.endian_conv = True
        elif format == 'wav':
            self.output = wave.open(filename, 'wb')
            self.endian_conv = False
        else:
            raise AudioProcessError('Unknown output format: ' + format)
        self.output.setparams(self.input.getparams())
    def run(self):
        nframes = self.input.getparams().nframes
        step = 1048576
        width = self.input.getparams().sampwidth
        for s in range(0, nframes, step):
            data = self.input.readframes(s, step)
            if self.endian_conv:
                data = endian_conv(data, width)
            self.output.writeframes(data)
        outfile.close()
