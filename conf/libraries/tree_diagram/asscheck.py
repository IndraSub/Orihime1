#!/usr/bin/env python3

from typing import List
from . import info
import re

def getAssFontsList(filename: str) -> List[str]:
    with open(filename, 'r', encoding='utf8') as f:
        lines = f.readlines()
    fontnames = []
    for l in lines:
        l = l.strip()
        if l.lower().startswith('style:'):
            # format is normally ignored
            fontnames.append(l[6:].strip().split(',')[1])
        elif l.lower().startswith('dialogue:'):
            fontnames += re.findall(r'{\\fn([^{}]+)}', l)
    return fontnames

def getFontsLinux() -> bool:
    import fontconfig
    fontnames = set()
    fonts = fontconfig.query()
    for i in range(0, len(fonts)):
        for lang, fullname in fonts[i].fullname:
            fontnames.add(fullname)
    return fontnames

def getFontsWindows() -> bool:
    import clr
    from System import Drawing
    fontnames = set()
    collection = Drawing.Text.InstalledFontCollection()
    for i in range(0, collection.Length):
        fontnames.add(collection[i].Name)
    return fontnames

fontnames = None
if info.system == 'Windows':
    fontnames = getFontsWindows()
else:
    fontnames = getFontsLinux()

def checkFont(fontname: str) -> bool:
    return fontname in fontnames

def checkAssFonts(filename: str) -> List[dict]:
    fonts = [*map(
        lambda fontname: {'FontFamily': fontname, 'IsInstalled': checkFont(fontname)},
        getAssFontsList(filename))]
    fonts.sort(key=lambda d: (d['IsInstalled'], d['FontFamily']))
    return fonts
