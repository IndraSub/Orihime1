from .utils import ConfigureError, merge_clips, get_working_directory
import pydub
import os
import sys
import subprocess
import xml.etree.ElementTree as ET

class TrimFrames:
    def __init__(self, frames):
        if len(frames) == 0:
            raise ConfigureError('TrimFrames: frames length is 0')
        self.frames = frames

    def __call__(self, core, clip):
        clips = [
            core.std.Trim(clip, first=first, last=last)
            for first, last in self.frames
        ]
        return merge_clips(clips)


class TrimAudio:
    def __init__(self, enabled, temporary, ffmpeg, mediainfo, file, frames):
        self.enabled = enabled
        if enabled and len(frames) == 0:
            raise ConfigureError('TrimFrames: frames length is 0')
        self.frames = frames
        self.file = get_working_directory(file)
        self.temporary = temporary
        self.ffmpeg = ffmpeg
        self.mediainfo = mediainfo

    def getAudioDelay(self) -> int:
        xmlstr = subprocess.run([
            self.mediainfo,
            '--Output=XML',
            self.file
        ], stdout=subprocess.PIPE).stdout.decode('utf8')
        xml = ET.fromstring(xmlstr)
        vdelay = None
        adelay = None
        for track in xml.iter('{https://mediaarea.net/mediainfo}track'):
            if track.attrib['type'] == 'Video':
                d = track.find('{https://mediaarea.net/mediainfo}Delay')
                if d is not None:
                    vdelay = float(d.text)
            elif track.attrib['type'] == 'Audio':
                d = track.find('{https://mediaarea.net/mediainfo}Delay')
                if d is not None:
                    adelay = float(d.text)
        if vdelay is None:
            print('[DEBUG][TrimAudio] AudioDelay: video delay not found', file=sys.stderr)
            vdelay = 0
        if adelay is None:
            print('[DEBUG][TrimAudio] AudioDelay: audio delay not found', file=sys.stderr)
            return 0
        delay = int((adelay - vdelay) * 1000)
        print(f'[DEBUG][TrimAudio] AudioDelay: {delay} ms', file=sys.stderr)
        return delay

    def __call__(self, core, clip):
        extractedAudio = os.path.join(self.temporary, 'audio-extracted.wav')
        trimmedAudio = os.path.join(self.temporary, 'audio-trimmed.wav')
        print('[DEBUG][TrimAudio] Extracting audio file, this may take a while on long videos...', file=sys.stderr)
        delay = self.getAudioDelay()
        subprocess.run(args=[
            self.ffmpeg,
            '-hide_banner',
            '-i', self.file,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-f', 'wav',
            extractedAudio],
            check=True, stderr=subprocess.PIPE)
        if self.enabled:
            print('[DEBUG][TrimAudio] Trimming audio file...', file=sys.stderr)
            src = pydub.AudioSegment.from_wav(extractedAudio)
            segments = []
            for first, last in self.frames:
                first_ms = first * clip.fps.denominator * 1000 / clip.fps.numerator - delay
                last_ms = (last + 1) * clip.fps.denominator * 1000 / clip.fps.numerator - delay
                segments.append(src[first_ms:last_ms])
            out = merge_clips(segments)
            out.export(trimmedAudio, format='wav')
        else:
            os.rename(extractedAudio, trimmedAudio)
        return clip