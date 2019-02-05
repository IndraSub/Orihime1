#!/usr/bin/env python3

import re
import subprocess
from typing import List
from . import info

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
            fontnames += re.findall(r'{\\fn([^{}\\]+)[^{}]*}', l)
    return list(set(fontnames))

def checkFontLinux(fontname: str) -> bool:
    i = 0
    while True:
        matched = subprocess.check_output([
            info.FC_MATCH,
            '-f', f'%{{family[{i}]}}', f':family={fontname}'
        ], encoding='utf-8')
        if matched == fontname:
            return True
        if matched == '':
            break
        i += 1
    return False

def checkFontWindows(fontname: str) -> bool:
    import clr # pylint: disable=unused-import
    from System import Drawing
    try:
        Drawing.FontFamily(fontname)
    except:
        return False
    return True

def checkFont(fontname: str) -> bool:
    if fontname.startswith('@'):
        fontname = fontname[1:]
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
