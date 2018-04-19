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
    return list(set(fontnames))

def checkFontLinux(fontname: str) -> bool:
    import fontconfig
    return bool(fontconfig.query(fontname)) or bool(fontconfig.query(':fullname=' + fontname))

def checkFontWindows(fontname: str) -> bool:
    import clr
    from System import Drawing
    try:
        Drawing.FontFamily(fontname)
    except:
        return False
    return True

def checkFont(fontname: str) -> bool:
    if info.system == 'Windows':
        return checkFontWindows(fontname)
    else:
        return checkFontLinux(fontname)

def checkAssFonts(filename: str) -> List[dict]:
    fonts = [*map(
        lambda fontname: {'FontFamily': fontname, 'IsInstalled': checkFont(fontname)},
        getAssFontsList(filename))]
    fonts.sort(key=lambda d: (d['IsInstalled'], d['FontFamily']))
    return fonts
