class Resolution:
    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)

    def __call__(self, core, clip):
        return core.fmtc.resample(
            clip,
            w=self.width,
            h=self.height,
            kernel='spline64', )