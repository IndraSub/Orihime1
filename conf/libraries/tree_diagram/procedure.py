#!/usr/bin/env python3

from typing import List, Tuple
import os
import os.path as path
import sys
import shutil

from . import *

import yaml

content = getWorkingContent()
temporary = path.join(getWorkingDirectory(), 'temporary')

def missionReport(title: str, output: str) -> None:
    writeEventName('Mission Report')
    working_directory = path.relpath(getWorkingDirectory())

    report = [
        {'Title': title},
        {"Temporary Files": path.join(working_directory, 'temporary')},
        {"Quality": content['quality']},
        {"Source": path.join(working_directory, content['source']['filename'])},
        {"Output": path.join(working_directory, output)},
    ]

    yaml.dump(report, sys.stdout, default_flow_style=False)
    message = 'Type your decision:'
    options = ['&Confirm', 'E&xit']
    answer = choices(message, options, 1)
    if answer == 1:
        exit()

def precleanTemporaryFiles() -> None:
    writeEventName('Checking temporary files')
    if not path.exists(temporary):
        os.makedirs(temporary)
    directoryFiles = os.listdir(temporary)
    if len(directoryFiles) == 0:
        print('Directory is clean.')
    else:
        message = 'Temporary files exist, the previous task may not finished normally. Do you want to clear them?'
        options = ['&Confirm', 'E&xit']
        answer = choices(message, options, 1)
        if answer == 0:
            shutil.rmtree(temporary)
            os.makedirs(temporary)
        else:
            exit()

def precheckSubtitle() -> None:
    if 'subtitle' not in content['source'] or not content['source']['subtitle']:
        return
    writeEventName('Checking if all fonts are installed')
    subtitle = os.path.join(getWorkingDirectory(), content['source']['subtitle']['filename'])
    fonts = checkAssFonts(subtitle)
    all_installed = True
    print('{:16}{:<32}{:<16}'.format('', 'FontFamily', 'IsInstalled'))
    print('{:16}{}'.format('', '-' * 48))
    for f in fonts:
        print('{:16}{}{:<16}'.format('', padUnicode(f['FontFamily'], 32), f['IsInstalled']))
        all_installed = all_installed and f['IsInstalled']
    message = 'Please make sure that all fonts are installed'
    options = ['&Confirm', 'E&xit']
    answer = choices(message, options, 0 if all_installed else 1)
    if answer == 1:
        exit()

def postProcessVideo(output: str) -> None:
    writeEventName('Post-process with VapourSynth & Rip video data with x265')
    vapoursynth_pipeline = [
        '--y4m',
        '--arg',
        f'current_working={getMissionFilePath(getWorkListFilePath(), 0)}',
        '--arg',
        f'temporary={temporary}',
        '--arg',
        f'ffmpeg={info.FFMPEG}',
        '--arg',
        f'mediainfo={info.MEDIAINFO}',
        os.path.join(info.root_directory, 'conf', 'misaka64.py'),
        '-',
    ]
    encoder = content['project']['encoder']
    encoder_binary = getattr(info, encoder.upper())
    encoder_params = content['project']['encoder_params'].split()
    if encoder.upper().startswith('X264'):
        encoder_params = ['-', '--demuxer', 'y4m'] + encoder_params + ['--output', output]
    elif encoder.upper().startswith('X265'):
        encoder_params = ['--y4m'] + encoder_params + ['--output', output, '-']
    else:
        print(f"Encoder {encoder} is not supported.")
        exit()
    invokePipeline([
        [info.VSPIPE] + vapoursynth_pipeline,
        [encoder_binary] + encoder_params
    ])
    assertFileWithExit(output)

def encodeAudio(trimmedAudio: str, encodedAudio: str) -> None:
    writeEventName('Recode audio data to AAC format with QAAC')
    invokePipeline([
        [info.FFMPEG, '-hide_banner', '-i', trimmedAudio, '-f', 'wav', '-vn', '-'],
        [info.QAAC, '--tvbr', '127', '--quality', '2', '--ignorelength', '-o', encodedAudio, '-'],
    ])
    assertFileWithExit(encodedAudio)

def mkvMerge(output: str, encodedAudio: str, encodedVideo: str, title: str) -> None:
    writeEventName('Merge audio & video data with MKVMerge')
    merge = ['-o', output, encodedVideo, encodedAudio]
    invokePipeline([[info.MKVMERGE] + merge])
    assertFileWithExit(output)

def mkvMetainfo(output: str, title: str) -> None:
    writeEventName('Edit video metainfo with MKVPropEdit')
    props = [
        output,
        '--edit', 'info', '--set', f'title={title}',
        '--edit', 'track:1', '--set', f'name={title}',
        '--edit', 'track:2', '--set', f'name={title}', '--set', 'language=jpn',
    ]
    invokePipeline([[info.MKVPROPEDIT] + props])
    assertFileWithExit(output)

def cleanTemporaryFiles() -> None:
    writeEventName('Clean Temporary Files')
    message = 'Processing flow completed, you may want to take a backup of mission temporary files.'
    options = ['&Clear', '&Reserve']
    answer = choices(message, options, 1)
    if answer == 0:
        shutil.rmtree(temporary)
        os.makedirs(temporary)

def missionComplete(output: str):
    writeEventName('Mission Complete')
    invokePipeline([['mediainfo', output]])

def main() -> None:
    title = content['title'].format(**content)
    output = content['output']['filename'].format(**content)

    missionReport(title, output)
    precleanTemporaryFiles()
    precheckSubtitle()

    output = path.join(getWorkingDirectory(), output)
    encodedVideo = path.join(temporary, 'video-encoded.mp4')
    trimmedAudio = path.join(temporary, 'audio-trimmed.wav')
    encodedAudio = path.join(temporary, 'audio-encoded.m4a')

    postProcessVideo(encodedVideo)
    encodeAudio(trimmedAudio, encodedAudio)
    mkvMerge(output, encodedAudio, encodedVideo, title)
    mkvMetainfo(output, title)
    cleanTemporaryFiles()
    missionComplete(output)

