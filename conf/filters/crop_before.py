class CropBefore:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __call__(self, core, clip):
        clip = core.std.CropAbs(clip, width=self.width, height=self.height)
        return clip
