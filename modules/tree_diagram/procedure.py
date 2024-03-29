#!/usr/bin/env python3

import os
import sys
import shutil
import logging
import time
import json
import yaml
import requests

from . import info
from .kit import writeEventName, assertFileWithExit, choices, padUnicode, ExitException
from .process_utils import invokePipeline
from .asscheck import checkAssFonts
from .video_utils import exportTimecodeMP4
from .audio_utils import extractAudio, trimAudio, encodeAudio, mergeAndTrimAudio
from .config_loader import ParseContext

logger = logging.getLogger('tree_diagram')

working_directory = os.path.join(info.root_directory, 'episodes')
temporary = os.path.join(working_directory, 'temporary')

info.working_directory = working_directory
info.temporary = temporary
info.autorun = False
info.report_endpoint = None

current_working = None
content = None

missions = None

def load_missions():
    global missions
    missions_path = os.path.join(working_directory, 'missions.yaml')
    if not os.path.exists(missions_path):
        logger.critical(f'{missions_path} not found')
        raise ExitException(-1)

    with open(missions_path, encoding='utf8') as f:
        missions = yaml.safe_load(f)
        if missions is None:
            missions = {}
        if 'report' in missions:
            info.report_endpoint = missions['report']

    info.autorun = missions.get('autorun', False)

def parseContentV1(content: dict) -> dict:
    with open(os.path.join(working_directory, content['project']), encoding='utf8') as f:
        descriptions = yaml.safe_load_all(f)
        try:
            content['project'] = next(project for project in descriptions if project['quality'] == content['quality'])
        except StopIteration:
            logger.critical(f'Quality "{content["quality"]}" in episode "{content["episode"]}" has no match in project configuration "{content["project"]}".')
            raise ExitException(-1)

    # replacements
    content['title'] = content['title'].format(**content)
    if 'split' not in content['source']:
        content['source']['split'] = False
    if content['source']['split']:
        content['source']['audio'] = content['source']['audio'].format(**content)
        content['source']['filename'] = content['source']['video'].format(**content)
    else:
        content['source']['filename'] = content['source']['filename'].format(**content)
    content['output']['filename'] = content['output']['filename'].format(**content)
    if 'subtitle' in content['source'] and content['source']['subtitle']:
        if 'filename' in content['source']['subtitle'] and content['source']['subtitle']['filename']:
            content['source']['subtitle']['filename'] = content['source']['subtitle']['filename'].format(**content)

    return content

def parseContentV2() -> dict:
    return ParseContext(working_directory, {
        '$include': os.path.relpath(current_working, working_directory)
    }).parse()

def loadCurrentWorking(idx: int) -> None:
    global current_working
    global content
    current_working = os.path.join(working_directory, missions['missions'][idx])
    if not os.path.exists(current_working):
        logger.critical(f'{current_working} not found')
        raise ExitException(-1)

    with open(current_working, encoding='utf8') as f:
        content = yaml.safe_load(f)

    if '$version' not in content or content['$version'] == 1:
        content = parseContentV1(content)
    elif content['$version'] == 2:
        content = parseContentV2()
    else:
        logger.critical(f'Unsupported config version: {content["$version"]}')
        raise ExitException(-1)

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
    ] if 'subtitle' in content['source'] and content['source']['subtitle']\
         and 'filename' in content['source']['subtitle'] and content['source']['subtitle']['filename'] else []
    report += [
        {"Output": os.path.join(working_directory, content['output']['filename'])},
    ]

    yaml.dump(report, sys.stdout, default_flow_style=False)
    message = 'Confirm?'
    options = ['&Confirm', 'E&xit']
    answer = 0
    if not info.autorun:
        answer = choices(message, options, answer)
    if answer == 1:
        raise ExitException()

    if info.report_endpoint is not None:
        report = f'[{info.node}] Mission Start: {content["title"]}'
        requests.post(info.report_endpoint, report.encode('utf-8'), timeout=30)

def precheckOutput() -> None:
    writeEventName('Check output file')
    output = os.path.join(working_directory, content['output']['filename'])
    output_exists = os.path.exists(output)
    if not output_exists:
        print('Output is clean.')
    else:
        message = 'Output file already exists, OVERWRITE?'
        options = ['&Confirm', 'E&xit']
        answer = 1
        if not info.autorun:
            answer = choices(message, options, answer)
        if answer == 1:
            raise ExitException()

def precleanTemporaryFiles() -> None:
    writeEventName('Check temporary files')
    if '+special' in content and 'skip_preclean_temporary_files' in content['+special']:
        print('Skipping precleanTemporaryFiles due to project configure.')
        print('NOTE: This is a special behavior, you may want to delete "+special" segment in your project configure.')
        return
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
            raise ExitException()

def precheckSubtitle() -> None:
    if 'subtitle' not in content['source'] or not content['source']['subtitle']:
        return
    if 'filename' not in content['source']['subtitle'] or not content['source']['subtitle']['filename']:
        return
    writeEventName('Check SSA fonts')
    subtitle = os.path.join(working_directory, content['source']['subtitle']['filename'])
    with open(subtitle, 'rb') as f:
        if f.read(2) != b'\xef\xbb':
            message = 'The SSA file has no BOM header, continue?'
            options = ['&Continue', 'E&xit']
            answer = 1
            if not info.autorun:
                answer = choices(message, options, answer)
            if answer == 1:
                raise ExitException()
    fonts = checkAssFonts(subtitle)
    all_installed = True
    print('{:16}{:<32}{:<16}'.format('', 'FontFamily', 'IsInstalled'))
    print('{:16}{}'.format('', '-' * 48))
    for f in fonts:
        print('{:16}{}{:<16}'.format('', padUnicode(f['FontFamily'], 32), f['IsInstalled']))
        all_installed = all_installed and f['IsInstalled']
    message = 'Please make sure that all fonts are installed:'
    options = ['&Confirm', 'E&xit']
    answer = 0 if all_installed else 1
    if not all_installed and not info.autorun:
        answer = choices(message, options, answer)
    if answer == 1:
        raise ExitException()

def exportTimecode() -> None:
    if not any(f == 'VFRToCFR' or (type(f) is dict and list(f.keys())[0] == 'VFRToCFR')
           for f in content['project']['flow']):
        return
    writeEventName('Export Timecodes')
    source = os.path.join(working_directory, content['source']['filename'])
    if not source.endswith('.mp4'):
        logger.critical('Exporting timecodes currently only supports MP4 source file.')
        raise ExitException(-1)
    exportTimecodeMP4(source=source, exportedTimecode=os.path.join(temporary, 'timecode.txt'))

def processVideo() -> None:
    output = os.path.join(temporary, 'video-encoded.mp4')
    writeEventName('Process video & Encode')
    if '+special' in content and 'skip_process_video' in content['+special']:
        print('Skipping processVideo due to project configure.')
        print('NOTE: This is a special behavior, you may want to delete "+special" segment in your project configure.')
        return
    tdinfo = dict(info)
    tdinfo['binaries'] = None # avoid envvar growing too large
    os.environ['TDINFO'] = json.dumps(tdinfo)
    os.environ['DISPLAY'] = '' # workaround to avoid usage of X
    vapoursynth_pipeline = [
        '-c',
        'y4m',
        os.path.join(info.root_directory, 'modules', 'misaka64.py'),
        '-',
    ]
    encoder = content['project']['encoder']
    if encoder.upper() not in info:
        logger.critical(f'Encoder {encoder} is not supported. See Environment Check output for supported encoder executables.')
        raise ExitException(-1)
    encoder_binary = info[encoder.upper()]
    encoder_params = content['project']['encoder_params'].split()
    if encoder.lower().startswith('x264'):
        encoder_params = ['-', '--demuxer', 'y4m'] + encoder_params + ['--output', output]
    elif encoder.lower().startswith('x265'):
        encoder_params = ['--y4m'] + encoder_params + ['--output', output, '-']
    elif encoder.lower().startswith('rav1e'):
        encoder_params = ['-'] + encoder_params + ['--output', os.path.join(temporary, 'video-encoded.ivf')]
    elif encoder.lower().startswith('svtav1'):
        encoder_params = ['-i', 'stdin'] + encoder_params + ['-b', os.path.join(temporary, 'video-encoded.ivf')]
    else:
        logger.critical(f"Encoder {encoder} is not supported.")
        raise ExitException(-1)
    invokePipeline([
        [info.VSPIPE] + vapoursynth_pipeline, True,
        [encoder_binary] + encoder_params
    ])
    assertFileWithExit(output)

def processAudio() -> None:
    writeEventName('Process audio & Encode')
    if '+special' in content and 'skip_process_audio' in content['+special']:
        print('Skipping processAudio due to project configure.')
        print('NOTE: This is a special behavior, you may want to delete "+special" segment in your project configure.')
        return
    if (content['source']['split']): # splitted audio & video source
        source = os.path.join(working_directory, content['source']['audio'])
        extractedAudio = os.path.join(temporary, 'audio-extracted.wav')
        trimmedAudio = os.path.join(temporary, 'audio-trimmed.wav')
        encodedAudio = os.path.join(temporary, 'audio-encoded.m4a')
        clipInfo = os.path.join(temporary, 'clipinfo.json')

        trim_frames = None
        if any(f == 'TrimFrames' or (isinstance(f, dict) and list(f.keys())[0] == 'TrimFrames')
               for f in content['project']['flow']):  # has TrimFrames
            trim_frames = content['source']['trim_frames']
        with open(clipInfo, 'r', encoding='utf-8') as clipInfoFile:
            clipInfo = json.loads(clipInfoFile.read())
        extractAudio(source, extractedAudio)
        trimAudio(source, extractedAudio, trimmedAudio, clipInfo['fps'], trim_frames)
        encodeAudio(extractedAudio, encodedAudio)
        assertFileWithExit(encodedAudio)

    else: # audio from video source file
        source = os.path.join(working_directory, content['source']['filename'])
        extractedAudio = os.path.join(temporary, 'audio-extracted.wav')
        trimmedAudio = os.path.join(temporary, 'audio-trimmed.wav')
        encodedAudio = os.path.join(temporary, 'audio-encoded.m4a')
        clipInfo = os.path.join(temporary, 'clipinfo.json')

        trim_frames = None
        if any(f == 'TrimFrames' or (type(f) is dict and list(f.keys())[0] == 'TrimFrames')
               for f in content['project']['flow']): # has TrimFrames
            trim_frames = content['source']['trim_frames']

        if any(f == 'MultiSource' or (type(f) is dict and list(f.keys())[0] == 'MultiSource')
               for f in content['project']['flow']): # has MultiSource
            idx = 0
            for filename in content['source']['filenames']:
                source = os.path.join(working_directory, filename)
                print(f'MultiSource: Preparing {filename}...')
                extractAudio(source, os.path.join(temporary, f'{idx}.aif'))
                idx += 1
            mergeAndTrimAudio(idx, trimmedAudio, trim_frames)
        else: # single source
            extractAudio(source, extractedAudio)
            with open(clipInfo, 'r', encoding='utf-8') as clipInfoFile:
                clipInfo = json.loads(clipInfoFile.read())
            trimAudio(source, extractedAudio, trimmedAudio, clipInfo['fps'], trim_frames)

        encodeAudio(trimmedAudio, encodedAudio)
        assertFileWithExit(encodedAudio)

def mkvMerge() -> None:
    output = os.path.join(working_directory, content['output']['filename'])
    encodedVideo = os.path.join(temporary, 'video-encoded.mp4')
    encodedAudio = os.path.join(temporary, 'audio-encoded.m4a')
    writeEventName('Mux audio & video into MKV')
    invokePipeline([[info.MKVMERGE, '-o', output, encodedVideo, encodedAudio]])
    assertFileWithExit(output)

def mkvMetainfo() -> None:
    title = content['title']
    output = os.path.join(working_directory, content['output']['filename'])
    writeEventName('Write MKV metainfo')
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
    if info.report_endpoint is not None:
        report = f'[{info.node}] Mission Complete: {content["title"]}'
        requests.post(info.report_endpoint, report.encode('utf-8'), timeout=30)

def syncContent():
    global content
    if hasattr(info, 'content'):
        content = info.content

def runMission():
    missionReport()
    try:
        processVideo()
        processAudio()
        mkvMerge()
        mkvMetainfo()
        cleanTemporaryFiles(force=True)
    except Exception as e:
        if info.report_endpoint is not None:
            report = f'[{info.node}] Mission Failed With Exception: {e}'
            requests.post(info.report_endpoint, report.encode('utf-8'), timeout=30)
        raise
    missionComplete()

def main() -> None:
    load_missions()
    for idx in range(len(missions['missions'])):
        loadCurrentWorking(idx)
        precleanTemporaryFiles()
        precheckOutput()
        precheckSubtitle()
        exportTimecode()
    for idx in range(len(missions['missions'])):
        loadCurrentWorking(idx)
        runMission()

def genVseditFile() -> None:
    writeEventName('Generate VSEdit Script')
    outputScript = os.path.join(temporary, f'vsedit_{content["title"]}_{content["quality"]}_{int(time.time())}.vpy')
    tdinfo = dict(info)
    tdinfo['binaries'] = None # avoid envvar growing too large
    tdinfoJson = json.dumps(tdinfo)
    with open(outputScript, 'w', encoding='utf-8') as f:
        f.write(f'''\
import os
import sys
sys.path = {repr(sys.path)}
os.environ['TDINFO'] = {repr(tdinfoJson)}
os.environ['PATH'] = {repr(os.environ['PATH'])}
''')
        if sys.platform == 'linux':
            f.write(f'''os.environ['LD_LIBRARY_PATH'] = {repr(os.environ['LD_LIBRARY_PATH'])}\n''')
        f.write('''from misaka64 import main\n''')
        f.write('''main()\n''')
    assertFileWithExit(outputScript)
    print(f'Generated script file: {outputScript}')

def genVsedit() -> None:
    load_missions()
    for idx in range(len(missions['missions'])):
        loadCurrentWorking(idx)
        genVseditFile()
