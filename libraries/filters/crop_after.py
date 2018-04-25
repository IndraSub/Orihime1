class CropAfter:
    def __init__(self, top, bottom):
        self.top = top
        self.bottom = bottom

    def __call__(self, core, clip):
        clip = core.std.CropRel(clip, left=0, right=0, top=self.top, bottom=self.bottom)
        return clip
