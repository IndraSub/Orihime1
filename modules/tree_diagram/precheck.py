#!/usr/bin/env python3

from typing import List, Tuple, TypeVar
import re
import os
import sys
import logging
import platform
import importlib
import importlib.util
import subprocess
import json

from .kit import writeEventName, choices

logger = logging.getLogger('tree_diagram')
prechecked = False

class Info(dict):
    def __init__(self, *args, **kwargs):
        super(Info, self).__init__(*args, **kwargs)
        self.__dict__ = self
        self.binaries = {}
        self.node = None
        self.system = None
        self.system_version = None
        self.root_directory = None
        self.PYTHON = None
        self.vsfilters = []
        self.avsfilters = []

info = Info()

def addPath(path: str) -> None:
    if not os.path.isdir(path):
        raise RuntimeError(f'addPath: {path} is not a directory')
    os.environ['PATH'] = path + os.pathsep + os.environ['PATH']

def addLibPath(path: str) -> None:
    if info.system == 'Windows':
        os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
    else: # info.system == 'Linux'
        if 'LD_LIBRARY_PATH' not in os.environ:
            os.environ['LD_LIBRARY_PATH'] = path
        else:
            os.environ['LD_LIBRARY_PATH'] = path + os.pathsep + os.environ['LD_LIBRARY_PATH']
        winepath = subprocess.check_output([info.WINEPATH, '-w', path]).decode().strip()
        if 'WINEPATH' not in os.environ:
            os.environ['WINEPATH'] = winepath
        else:
            os.environ['WINEPATH'] = winepath + ';' + os.environ['WINEPATH']

def addPythonPath(path: str) -> None: # This one is appended after the current path
    if not os.path.exists(path):
        raise RuntimeError(f'addPythonPath: {path} is not found')
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = path
    else:
        os.environ['PYTHONPATH'] += os.pathsep + path
    sys.path.append(path)

def checkSystem() -> None:
    plat_info = platform.uname()
    logger.info('PYTHON VERSION: %s', sys.version.replace('\n', ''))
    logger.info('PYTHON EXECUTABLE: %s', sys.executable)
    logger.info('NODE: %s', plat_info.node)
    logger.info('SYSTEM: %s', plat_info.system)
    if plat_info.system == 'Windows':
        release = plat_info.version
    else:
        release = plat_info.release
    logger.info('RELEASE: %s', release)
    logger.info('MACHINE: %s', plat_info.machine)

    default_encoding = sys.getdefaultencoding()
    logger.info('ENCODING: %s', default_encoding)

    passed = True
    #if sys.version_info < (3, 6) or sys.version_info > (3, 10):
    #    logger.error('Python version should be 3.6, 3.7, 3.8 or 3.9')
    #    passed = False
    if plat_info.system not in ['Windows', 'Linux']:
        logger.error('Unsupported operating system, supported: Windows, Linux')
        passed = False
    if plat_info.machine not in ['i386', 'x86_64', 'AMD64']:
        logger.error('Unsupported platform, supported: i386, x86_64, amd64')
        passed = False
    if default_encoding != 'utf-8':
        logger.error('Unsupported encoding, supported: utf-8')
        passed = False
    if not passed:
        sys.exit(-1)
    info.node = plat_info.node
    info.system = plat_info.system
    info.system_version = release
    info.PYTHON = sys.executable

def setRootDirectory() -> None:
    script_path = os.path.realpath(__file__)
    script_directory = os.path.dirname(script_path)
    info.root_directory = os.path.abspath(os.path.join(script_directory, '..', '..'))

def assertModulesInstalled(modules: List[Tuple[str, str]]) -> None:
    not_found = []
    for module in modules:
        if importlib.util.find_spec(module[0]) is None:
            not_found.append(module[1])
    if len(not_found) > 0:
        logger.critical(f'Modules not found: {", ".join(not_found)}, install missing modules first')
        message = 'You can choose Continue to skip installing missing modules at YOUR OWN RISK.'
        options = ['&Continue', 'E&xit']
        answer = 1
        answer = choices(message, options, answer)
        if answer == 1:
            sys.exit(-1)

def findExecutable(filename: str, shorthand=None) -> str:
    filepath = None
    paths = os.environ['PATH'].split(os.pathsep)
    if info.system == 'Windows':
        paths = [os.getcwd()] + paths

    for path in paths:
        file_test = os.path.join(path, filename)
        if os.path.exists(file_test) and os.path.isfile(file_test) and os.access(file_test, os.X_OK):
            filepath = file_test
            break

    if shorthand is None:
        shorthand = os.path.basename(filename).upper()
        if info.system == 'Windows':
            # remove extensions
            exts = os.environ['PATHEXT'].split(os.pathsep)
            ext = list(filter(lambda ext: shorthand.endswith(ext.upper()), exts))
            if ext:
                shorthand = shorthand[:-len(ext[0])]

    shorthand = shorthand.upper()
    shorthand = re.sub(r'[^A-Z0-9]', '_', shorthand)
    if shorthand[0] in [str(i) for i in range(0,10)]:
        shorthand = '_' + shorthand
    if isinstance(shorthand, str):
        info[shorthand] = filepath

    logger.info(f'{shorthand} EXECUTABLE: {filepath}')
    return filepath

def loadBinaryInfo(filename: str):
    if filename != os.path.realpath(filename):
        raise Exception('must use real path (no symlinks)')
    fileinfo = {}
    fileinfo['mtime'] = os.path.getmtime(filename)
    with open(filename, 'rb') as f:
        head = f.read(4)
        if head == b'\x7fELF':
            fileformat = 'ELF'
        elif head[:2] == b'MZ':
            fileformat = 'PE'
        else:
            fileformat = 'unknown'
    fileinfo['fileformat'] = fileformat
    if fileformat == 'ELF':
        # pylint: disable=import-error
        # pylint: disable=import-outside-toplevel
        from elftools.elf.elffile import ELFFile
        with open(filename, 'rb') as f:
            elf = ELFFile(f)
            if elf.header.e_type == 'ET_EXEC':
                filetype = 'executable'
            elif elf.header.e_type == 'ET_DYN':
                if elf.get_section_by_name('.interp'):
                    filetype = 'executable'
                else:
                    filetype = 'library'
            else:
                filetype = 'unknown'
            fileinfo['filetype'] = filetype
            fileinfo['bits'] = elf.elfclass
            dependencies = []
            rpath = []
            runpath = []
            dynamic = elf.get_section_by_name('.dynamic')
            if dynamic:
                for tag in dynamic.iter_tags():
                    if tag.entry.d_tag == 'DT_NEEDED':
                        dependencies.append(tag.needed)
                    elif tag.entry.d_tag == 'DT_RPATH':
                        rpath.append(tag.rpath)
                    elif tag.entry.d_tag == 'DT_RUNPATH':
                        runpath.append(tag.runpath)
            fileinfo['dependencies'] = dependencies
            fileinfo['rpath'] = rpath
            fileinfo['runpath'] = runpath
            exports = []
            dynsym = elf.get_section_by_name('.dynsym')
            if dynsym:
                for symbol in dynsym.iter_symbols():
                    if symbol.entry.st_shndx != 'SHN_UNDEF':
                        exports.append(symbol.name)
            fileinfo['exports'] = exports
    elif fileformat == 'PE':
        # pylint: disable=import-error
        # pylint: disable=import-outside-toplevel
        from pefile import PE
        pe = PE(filename, fast_load=True)
        try:
            pe.parse_data_directories()
            if pe.is_exe():
                filetype = 'executable'
            elif pe.is_dll():
                filetype = 'library'
            else:
                filetype = 'unknown'
            fileinfo['filetype'] = filetype
            # https://msdn.microsoft.com/en-us/library/windows/desktop/ms680313(v=vs.85).aspx
            fileinfo['bits'] = 32 if pe.FILE_HEADER.Machine == 0x014c else 64
            dependencies = []
            if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dependencies.append(entry.dll.decode())
            if hasattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT'):
                for entry in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
                    dependencies.append(entry.dll.decode())
            fileinfo['dependencies'] = dependencies
            exports = []
            if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
                for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if symbol.name:
                        exports.append(symbol.name.decode())
            fileinfo['exports'] = exports
        finally:
            pe.close()
    info.binaries[filename] = fileinfo

wine_paths = None
windir = None
def resolveDependency(filepath: str) -> None:
    global wine_paths, windir
    filepath = os.path.realpath(filepath)
    if filepath not in info.binaries:
        loadBinaryInfo(filepath)
    fileinfo = info.binaries[filepath]
    if 'dependencies_link' in fileinfo:
        return
    if fileinfo['fileformat'] != 'PE' and fileinfo['fileformat'] != 'ELF':
        return
    dependencies_link = []
    for depname in fileinfo['dependencies']:
        findpaths = []
        ignore_case = False
        if fileinfo['fileformat'] == 'PE':
            # https://msdn.microsoft.com/en-us/library/windows/desktop/ms682586(v=vs.85).aspx#search_order_for_desktop_applications
            findpaths.append(os.path.dirname(filepath))
            if platform.architecture()[0] == '64bit' and fileinfo['bits'] == 32:
                findpaths.append(os.path.join(windir, 'syswow64'))
            else:
                findpaths.append(os.path.join(windir, 'system32'))
            findpaths.append(windir)
            if info.system == 'Linux':
                if not wine_paths:
                    wine_paths = [*map(lambda p: subprocess.check_output([info.WINEPATH, '-u', p]).decode().strip(),
                        subprocess.check_output([info.WINE, 'cmd', '/c', 'echo %PATH%']).decode().strip().split(';'))]
                findpaths += wine_paths
                ignore_case = True
            else:
                findpaths += os.environ['PATH'].split(os.pathsep)
        elif fileinfo['fileformat'] == 'ELF':
            # man ld.so
            origin = os.path.dirname(filepath)
            lib = 'lib64' if fileinfo['bits'] == 64 else 'lib'
            pl = platform.machine()
            def replace_rpath(p: str):
                p = re.sub(r'\$ORIGIN(?=[^a-zA-Z0-9\s]|$)', origin, p)
                p = re.sub(r'\${ORIGIN}', origin, p)
                p = re.sub(r'\$LIB(?=[^a-zA-Z0-9\s]|$)', lib, p)
                p = re.sub(r'\${LIB}', lib, p)
                p = re.sub(r'\$PLATFORM(?=[^a-zA-Z0-9\s]|$)', pl, p)
                p = re.sub(r'\${PLATFORM}', pl, p)
                return p
            for rpath in fileinfo['rpath']:
                findpaths.append(replace_rpath(rpath))
            if 'LD_LIBRARY_PATH' in os.environ:
                findpaths += os.environ['LD_LIBRARY_PATH'].split(os.pathsep)
            for runpath in fileinfo['runpath']:
                findpaths.append(replace_rpath(runpath))
            if fileinfo['bits'] == 64:
                findpaths += ['/lib64', '/usr/lib64', '/usr/local/lib64',
                              '/lib/x86_64-linux-gnu', '/usr/lib/x86_64-linux-gnu',
                              '/usr/local/lib/x86_64-linux-gnu']
            else:
                findpaths += ['/lib32', '/usr/lib32', '/usr/local/lib32',
                              '/lib/i386-linux-gnu', '/usr/lib/i386-linux-gnu',
                              '/usr/local/lib/i386-linux-gnu']
            findpaths += ['/lib', '/usr/lib', '/usr/local/lib']
        depfilepath = None
        for path in findpaths:
            if ignore_case and os.path.isdir(path):
                for fname in os.listdir(path):
                    if depname.lower() == fname.lower():
                        depfilepath = os.path.join(path, fname)
                        break
            else:
                file_test = os.path.join(path, depname)
                if os.path.exists(file_test) and os.path.isfile(file_test):
                    depfilepath = file_test
                    break
        if depfilepath:
            depfilepath = os.path.realpath(depfilepath)
        dependencies_link.append(depfilepath)
    fileinfo['dependencies_link'] = dependencies_link

def queryDependency(filepath: str, debug=False, circular=set()) -> List[str]:
    global windir
    filepath = os.path.realpath(filepath)
    if info.system == 'Windows':
        if filepath.lower().startswith(windir.lower() + '\\'):
            return []
    elif windir:
        if filepath.startswith(windir + '/'):
            return []
    if filepath not in info.binaries or 'dependencies_link' not in info.binaries[filepath]:
        resolveDependency(filepath)
    fileinfo = info.binaries[filepath]
    if 'checked' in fileinfo and not debug:
        return []
    if fileinfo['fileformat'] != 'PE' and fileinfo['fileformat'] != 'ELF':
        return []
    result = []
    for i in range(0, len(fileinfo['dependencies'])):
        depname = fileinfo['dependencies'][i]
        deppath = fileinfo['dependencies_link'][i]
        depquery = []
        if deppath:
            if depname in circular:
                if debug:
                    depquery = [f'{depname} => (circular)']
            else:
                c = circular.copy()
                c.add(depname)
                depquery = [*map(lambda s: '    ' + s, queryDependency(deppath, debug, c))]
                if depquery or debug:
                    depquery = [f'{depname} => {deppath}'] + depquery
        elif depname.startswith('api-ms-win') and info.system == 'Windows' and int(info.system_version.split('.')[0]) >= 10:
            if debug:
                depquery = [f'{depname} => (internal)']
        else:
            depquery = [f'{depname} => NOT FOUND']
        result += depquery
    if not result:
        fileinfo['checked'] = True
    return result

ExecDescription = TypeVar('ExecDescription', Tuple[str, bool, str], Tuple[str, bool])
def checkExecutables(executables: List[ExecDescription]) -> None:
    not_found = []
    for exe in executables:
        shorthand = exe[2] if len(exe) > 2 else None
        filepath = findExecutable(exe[0], shorthand)
        if exe[1] and filepath is None:
            not_found.append(exe[0])
        elif filepath is not None:
            depinfo = queryDependency(filepath)
            if depinfo:
                logger.warning('%s:', filepath)
                for l in depinfo:
                    logger.warning('    %s', l)
    if len(not_found) > 0:
        logger.critical('Executables not found: %s', ', '.join(not_found))
        sys.exit(-1)

def findVSPlugins() -> List[str]:
    result = []
    plugin_dir = os.path.join(info.root_directory, 'binaries', info.system.lower(), 'filter_plugins', 'vs')
    init_names = {'VapourSynthPluginInit', 'VapourSynthPluginInit2', '_VapourSynthPluginInit@12', '_VapourSynthPluginInit2@8'}
    for root, _, files in os.walk(plugin_dir):
        for name in files:
            path = os.path.join(root, name)
            if path.lower().endswith('.dll') or (info.system == 'Linux' and path.endswith('.so')):
                path = os.path.realpath(path)
                if path not in info.binaries:
                    loadBinaryInfo(path)
                fileinfo = info.binaries[path]
                if 'exports' not in fileinfo:
                    continue
                isPlugin = False
                for func_name in fileinfo['exports']:
                    if func_name in init_names:
                        isPlugin = True
                        break
                if isPlugin:
                    result.append(path)
                    depinfo = queryDependency(path)
                    if depinfo:
                        logger.warning('%s:', path)
                        for l in depinfo:
                            logger.warning('    %s', l)
    return result

def findAVSPlugins() -> List[str]:
    result = []
    plugin_dir = os.path.join(info.root_directory, 'binaries', info.system.lower(), 'filter_plugins', 'avs')
    init_names = {
        'AvisynthPluginInit3', '_AvisynthPluginInit3@8',
        'AvisynthPluginInit2', '_AvisynthPluginInit2@4',
    }
    for root, _, files in os.walk(plugin_dir):
        for name in files:
            path = os.path.join(root, name)
            if path.lower().endswith('.dll') or (info.system == 'Linux' and path.endswith('.so')):
                path = os.path.realpath(path)
                if path not in info.binaries:
                    loadBinaryInfo(path)
                fileinfo = info.binaries[path]
                if 'exports' not in fileinfo:
                    continue
                isPlugin = False
                for func_name in fileinfo['exports']:
                    if func_name in init_names:
                        isPlugin = True
                        break
                if isPlugin:
                    result.append(path)
                    depinfo = queryDependency(path)
                    if depinfo:
                        logger.warning('%s:', path)
                        for l in depinfo:
                            logger.warning('    %s', l)
    return result

def loadBinCache():
    cachepath = os.path.join(info.root_directory, 'bin_cache.json')
    cache = {}
    if os.path.exists(cachepath):
        with open(cachepath, 'r', encoding='utf-8') as f:
            cache = json.loads(f.read())
    else:
        logger.info('*** Binary cache file not found. Analyzing binary files on site. It may take a while... ***')
    info.binaries = cache.get('binaries', {})
    try:
        for filepath in info.binaries.keys():
            if not os.path.isfile(filepath):
                del info.binaries[filepath]
                continue
            fileinfo = info.binaries[filepath]
            if os.path.getmtime(filepath) != fileinfo.get('mtime'):
                del info.binaries[filepath]
                continue
    except RuntimeError:
        logger.error('*** Outdated binary cache file, please delete bin_cache.json manually, then re-run this script. ***')
        sys.exit(-1)

def saveBinCache():
    cachepath = os.path.join(info.root_directory, 'bin_cache.json')
    with open(cachepath, 'w', encoding='utf-8') as f:
        f.write(json.dumps({
            'binaries': info.binaries,
        }))

def precheck() -> None:
    global windir, prechecked

    if prechecked:
        return

    writeEventName('Environment Check')
    
    if 'TDDEBUG' in os.environ and os.environ['TDDEBUG'] == '1':
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    checkSystem()
    setRootDirectory()
    loadBinCache()

    if info.system == 'Linux':
        checkExecutables([('wine', True), ('winepath', True)])

    addPath(os.path.join(info.root_directory, 'binaries', info.system.lower()))
    addLibPath(os.path.join(info.root_directory, 'binaries', info.system.lower(), 'libraries'))
    addPythonPath(os.path.join(info.root_directory, 'modules'))

    if info.system == 'Windows':
        windir = os.environ['WINDIR']
    else:
        windir = subprocess.check_output([info.WINEPATH, '-u', r'C:\windows']).decode().strip()

    required_modules = [
        ('yaml', 'PyYAML'),
        ('pefile', 'pefile'),
        ('requests', 'requests'),
        ('jsonpath2', 'jsonpath2'),
        ('rich', 'rich'),
    ]
    if info.system == 'Windows':
        required_modules += [
            ('clr', 'pythonnet'),
        ]
    else:
        required_modules += [
            ('elftools', 'pyelftools'),
        ]
    assertModulesInstalled(required_modules)

    if info.system == 'Windows':
        executables = [
            # filename, required[, shorthand]
            ('vspipe.exe', True),
            ('ffmpeg.exe', True),
            ('mediainfo.exe', True),
            ('mkvmerge.exe', True),
            ('mkvpropedit.exe', True),
            ('mp4fpsmod.exe', True),
            ('qaac64.exe', True, 'qaac'),
            ('x264.exe', False, 'x264'),
            ('x264-7mod.exe', False, 'x264_7mod'),
            ('x264-7mod-10bit.exe', False, 'x264_7mod_10bit'),
            ('x264-tmod.exe', False, 'x264_tmod'),
            ('x264-yuuki.exe', False, 'x264_yuuki'),
            ('x265.exe', False, 'x265'),
            ('x265-asuna.exe', False, 'x265_asuna'),
            ('x265-asuna-10bit.exe', False, 'x265_asuna_10bit'),
            ('x265-asuna-full.exe', False, 'x265_asuna_full'),
            ('x265-yuuki.exe', False, 'x265_yuuki'),
            ('x265-yuuki-10bit.exe', False, 'x265_yuuki_10bit'),
            ('x265-yuuki-full.exe', False, 'x265_yuuki_full'),
        ]
    else:
        executables = [
            ('vspipe', True),
            ('ffmpeg', True),
            ('mediainfo', True),
            ('mkvmerge', True),
            ('mkvpropedit', True),
            ('mp4fpsmod', True),
            ('qaac', True),
            ('fc-match', True), # fontconfig
            ('x264', False),
            ('x264-7mod', False),
            ('x264-7mod-10bit', False),
            ('x264-tmod', False),
            ('x265', False),
            ('x265-asuna', False),
            ('x265-asuna-10bit', False),
            ('x265-yuuki', False),
            ('x265-yuuki-10bit', False),
        ]
    checkExecutables(executables)

    info.vsfilters = findVSPlugins()
    info.avsfilters = findAVSPlugins()
    print(f'External VapourSynth Plugins #: {len(info.vsfilters)}')
    print(f'External AviSynth Plugins #: {len(info.avsfilters)}')
    saveBinCache()
    prechecked = True
