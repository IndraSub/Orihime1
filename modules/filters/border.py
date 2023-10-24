from .utils import ConfigureError, SimpleFilter

@SimpleFilter
def Crop(core, clip, _, left=0, right=0, top=0, bottom=0):
    return core.std.Crop(clip, left=left, right=right, top=top, bottom=bottom)

@SimpleFilter
def CropAbs(core, clip, _, width, height, left=0, top=0):
    return core.std.CropAbs(clip, width=width, height=height, left=left, top=top)

@SimpleFilter
def AddBorders(core, clip, _, left=0, right=0, top=0, bottom=0, color=[0,0,0]):
    return core.std.AddBorders(clip, left=left, right=right, top=top, bottom=bottom, color=color)
