from third_party import vsTAAmbk as taa

from .utils import SimpleFilter


@SimpleFilter
def TAAmbk(core, clip, _, aatype=1, strength=0.0, preaa=0,
           cycle=0, down8=False, mtype=5, mthr=24, txtmask=0, txtfade=0,
           thin=0, dark=0.0, sharp=0, aarepair=0, postaa=False, stabilize=0,
           opencl=True, showmask=0):
    return taa.TAAmbk(clip, aatype, strength, preaa, cycle, down8,
                      mtype, mthr, txtmask, txtfade, thin, dark,
                      sharp, aarepair, postaa, stabilize, opencl, showmask)
