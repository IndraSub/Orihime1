#!/usr/bin/env python3

from typing import List, Tuple
import os
import sys
import shutil
import io
import logging
import json

from . import info
from .kit import writeEventName, assertFileWithExit, choices, padUnicode
from .process_utils import invokePipeline
from .asscheck import checkAssFonts
from .audio_utils import extractAudio, trimAudio, encodeAudio

import yaml

logger = logging.getLogger('tree_diagram')

working_directory = os.path.join(info.root_directory, 'episodes')
temporary = os.path.join(working_directory, 'temporary')

missions_path = os.path.join(working_directory, 'missions.yaml')
if not os.path.exists(missions_path):
    logger.critical(f'{missions_path} not found')
    exit(-1)

with open(missions_path, encoding='utf8') as f:
    missions = yaml.load(f)

current_working = None

info.working_directory = working_directory
info.temporary = temporary
info.autorun = missions.get('autorun')

def loadCurrentWorking(mission) -> None:
    current_working = os.path.join(working_directory, mission)
    if not os.path.exists(current_working):
        logger.critical(f'{current_working} not found')
        exit(-1)

    with open(current_working, encoding='utf8') as f:
        content = yaml.load(f)

    with open(os.path.join(working_directory, content['project']), encoding='utf8') as f:
        descriptions = yaml.load_all(f)
        content['project'] = next(project for project in descriptions if project['quality'] == content['quality'])

    # replacements
    content['title'] = content['title'].format(**content)
    content['source']['filename'] = content['source']['filename'].format(**content)
    content['output']['filename'] = content['output']['filename'].format(**content)
    if 'subtitle' in content['source'] and content['source']['subtitle']:
        content['source']['subtitle']['filename'] = content['source']['subtitle']['filename'].format(**content)

    info.current_working = current_working
    info.content = content

def missionReport() -> None:
    writeEventName('Mission Report')

    report = [
        {'Title': content['title']},
        {"Temporary Files": temporary},
        {"Quality": content['quality']},
        {"Source": os.path.join(working_directory, content['source']['filename'])}
    ]
    report += [
        {"Subtitle": os.path.join(working_directory, content['source']['subtitle']['filename'])}
    ] if 'subtitle' in content['source'] and content['source']['subtitle'] else []
    report += [
        {"Output": os.path.join(working_directory, content['output']['filename'])},
    ]

    yaml.dump(report, sys.stdout, default_flow_style=False)

    output_exists = os.path.exists(output)
    message = 'Please confirm the mission:' if not output_exists else 'Output file already exists, OVERWRITE?'
    options = ['&Confirm', 'E&xit']
    output = os.path.join(working_directory, content['output']['filename'])
    answer = 0 if not output_exists else 1
    if not info.autorun:
        answer = choices(message, options, answer)
    if answer == 1:
        exit()

def precleanTemporaryFiles() -> None:
    writeEventName('Checking temporary files')
    if not os.path.exists(temporary):
        os.makedirs(temporary)
    directoryFiles = os.listdir(temporary)
    if len(directoryFiles) == 0:
        print('Directory is clean.')
    else:
        message = 'Temporary files exist, the previous task may not finished normally. Do you want to clear them?'
        options = ['&Confirm', 'E&xit']
        answer = 1
        if not info.autorun:
            answer = choices(message, options, answer)
        if answer == 0:
            shutil.rmtree(temporary)
            os.makedirs(temporary)
        else:
            exit()

def precheckSubtitle() -> None:
    if 'subtitle' not in content['source'] or not content['source']['subtitle']:
        return
    writeEventName('Checking if all fonts are installed')
    subtitle = os.path.join(working_directory, content['source']['subtitle']['filename'])
    fonts = checkAssFonts(subtitle)
    all_installed = True
    print('{:16}{:<32}{:<16}'.format('', 'FontFamily', 'IsInstalled'))
    print('{:16}{}'.format('', '-' * 48))
    for f in fonts:
        print('{:16}{}{:<16}'.format('', padUnicode(f['FontFamily'], 32), f['IsInstalled']))
        all_installed = all_installed and f['IsInstalled']
    message = 'Please make sure that all fonts are installed'
    options = ['&Confirm', 'E&xit']
    answer = 0 if all_installed else 1
    if not all_installed and not info.autorun:
        answer = choices(message, options, answer)
    if answer == 1:
        exit()

def processVideo() -> None:
    output = os.path.join(temporary, 'video-encoded.mp4')
    writeEventName('Process video with VapourSynth & Encode')
    tdinfo = dict(info)
    tdinfo['binaries'] = None # avoid envvar growing too large
    os.environ['TDINFO'] = json.dumps(tdinfo)
    vapoursynth_pipeline = [
        '--y4m',
        os.path.join(info.root_directory, 'libraries', 'misaka64.py'),
        '-',
    ]
    encoder = content['project']['encoder']
    encoder_binary = info[encoder.upper()]
    encoder_params = content['project']['encoder_params'].split()
    if encoder.lower().startswith('x264'):
        encoder_params = ['-', '--demuxer', 'y4m'] + encoder_params + ['--output', output]
    elif encoder.lower().startswith('x265'):
        encoder_params = ['--y4m'] + encoder_params + ['--output', output, '-']
    else:
        print(f"Encoder {encoder} is not supported.")
        exit(-1)
    invokePipeline([
        [info.VSPIPE] + vapoursynth_pipeline,
        [encoder_binary] + encoder_params
    ])
    assertFileWithExit(output)

def processAudio() -> None:
    source = os.path.join(working_directory, content['source']['filename'])
    extractedAudio = os.path.join(temporary, 'audio-extracted.wav')
    trimmedAudio = os.path.join(temporary, 'audio-trimmed.wav')
    encodedAudio = os.path.join(temporary, 'audio-encoded.m4a')
    trim_frames = None
    if content['project']['flow'].get('TrimFrames', False):
        trim_frames = content['source']['trim_frames']
    writeEventName('Trim audio & Encode')
    extractAudio(source, extractedAudio)
    trimAudio(source, extractedAudio, trimmedAudio, trim_frames)
    encodeAudio(trimmedAudio, encodedAudio)
    assertFileWithExit(encodedAudio)

def mkvMerge() -> None:
    output = os.path.join(working_directory, content['output']['filename'])
    encodedVideo = os.path.join(temporary, 'video-encoded.mp4')
    encodedAudio = os.path.join(temporary, 'audio-encoded.m4a')
    writeEventName('Merge audio & video data with MKVMerge')
    invokePipeline([[info.MKVMERGE, '-o', output, encodedVideo, encodedAudio]])
    assertFileWithExit(output)

def mkvMetainfo() -> None:
    title = content['title']
    output = os.path.join(working_directory, content['output']['filename'])
    writeEventName('Edit video metainfo with MKVPropEdit')
    props = [
        output,
        '--edit', 'info', '--set', f'title={title}',
        '--edit', 'track:1', '--set', f'name={title}',
        '--edit', 'track:2', '--set', f'name={title}', '--set', 'language=jpn',
    ]
    invokePipeline([[info.MKVPROPEDIT] + props])
    assertFileWithExit(output)

def cleanTemporaryFiles(force=False) -> None:
    writeEventName('Clean Temporary Files')
    message = 'Processing flow completed, you may want to take a backup of mission temporary files.'
    options = ['&Clear', '&Reserve']
    answer = 0
    if not info.autorun and not force:
        answer = choices(message, options, answer)
    if answer == 0:
        shutil.rmtree(temporary)
        os.makedirs(temporary)

def missionComplete():
    output = os.path.join(working_directory, content['output']['filename'])
    writeEventName('Mission Complete')
    invokePipeline([[info.MEDIAINFO, output]])

def main() -> None:
    for mission in missions['missions']:
        loadCurrentWorking(mission)
        missionReport()
        precheckSubtitle()
    precleanTemporaryFiles()
    for mission in missions['missions']:
        loadCurrentWorking(mission)
        processVideo()
        processAudio()
        mkvMerge()
        mkvMetainfo()
        cleanTemporaryFiles(force=True)
        missionComplete()
