from vapoursynth_tools import finesharp as fs

from .utils import ConfigureError

class UnsharpMasking:
    def __init__(self, strength, final):
        self.strength = float(strength)
        self.final = float(final)
        if final >= 0.25:
            message = 'FineSharp: final XSharpen\'s threshold should small than 0.25 (currently ' + str(final) + ')'
            raise ConfigureError(message)

    def __call__(self, core, clip):
        return fs.sharpen(clip, sstr=self.strength, xstr=self.final)