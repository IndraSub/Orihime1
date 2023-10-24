class LineSharp:
    def __init__(self, _):
        pass
    def __call__(self, core, clip):
        return core.warp.AWarpSharp2(
            clip,
            thresh=128,
            blur=3,
            type=1,
            depth=16,
            chroma=0, )