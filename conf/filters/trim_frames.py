from .utils import ConfigureError, merge_clips, get_working_directory
import pydub
import os
import sys
import subprocess

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
    def __init__(self, enabled, temporary, ffmpeg, file, frames):
        self.enabled = enabled
        if enabled and len(frames) == 0:
            raise ConfigureError('TrimFrames: frames length is 0')
        self.rawframes = []
        for first, last in frames:
            self.rawframes.append([round(first / 4 * 5), round(last / 4 * 5)])
        self.file = get_working_directory(file)
        self.temporary = temporary
        self.ffmpeg = ffmpeg

    def __call__(self, core, clip):
        extractedAudio = os.path.join(self.temporary, 'audio-extracted.wav')
        trimmedAudio = os.path.join(self.temporary, 'audio-trimmed.wav')
        print('[DEBUG][TrimAudio] Extracting audio file, this may take a while on long videos...', file=sys.stderr)
        subprocess.run(args=[
            self.ffmpeg,
            '-hide_banner',
            '-i', self.file,
            '-vn',
            '-af', 'aresample=async=1:first_pts=0',
            '-acodec', 'pcm_s16le',
            '-f', 'wav',
            extractedAudio],
            check=True, stderr=subprocess.PIPE)
        if self.enabled:
            print('[DEBUG][TrimAudio] Trimming audio file...', file=sys.stderr)
            src = pydub.AudioSegment.from_wav(extractedAudio)
            segments = []
            for first, last in self.rawframes:
                first_ms = first * clip.fps.denominator * 1000 / clip.fps.numerator
                last_ms = (last + 1) * clip.fps.denominator * 1000 / clip.fps.numerator
                segments.append(src[first_ms:last_ms])
            out = merge_clips(segments)
            out.export(trimmedAudio, format='wav')
        else:
            os.rename(extractedAudio, trimmedAudio)
        return clip