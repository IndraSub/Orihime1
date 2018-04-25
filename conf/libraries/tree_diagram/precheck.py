#!/usr/bin/env python3

from typing import List, Tuple, TypeVar
import re
import os
import sys
import logging
import platform
import importlib
import string
import subprocess
import json

logger = logging.getLogger('tree_diagram')

class Info(dict):
    def __init__(self, *args, **kwargs):
        super(Info, self).__init__(*args, **kwargs)
        self.__dict__ = self

info = Info()
info.binaries = {}

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
        winpath = subprocess.check_output([info.WINEPATH, '-w', path]).decode().strip()
        if 'WINEPATH' not in os.environ:
            os.environ['WINEPATH'] = path
        else:
            os.environ['WINEPATH'] = path + ';' + os.environ['WINEPATH']

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
    logger.info('PYTHON VERSION: {}'.format(sys.version.replace('\n', '')))
    logger.info(f'PYTHON EXECUTABLE: {sys.executable}')
    logger.info(f'SYSTEM: {plat_info.system}')
    if plat_info.system == 'Windows':
        release = plat_info.version
    else:
        release = plat_info.release
    logger.info(f'RELEASE: {release}')
    logger.info(f'MACHINE: {plat_info.machine}')

    passed = True
    if sys.version_info < (3, 6):
        logger.error('Python version should be no less than 3.6')
        passed = False
    if plat_info.system not in ['Windows', 'Linux']:
        logger.error('Unsupported operating system')
        passed = False
    if plat_info.machine not in ['i386', 'x86_64', 'AMD64']:
        logger.error('Unsupported processor')
        passed = False
    if not passed:
        exit(-1)
    info.system = plat_info.system
    info.system_version = release
    info.PYTHON = sys.executable

def setRootDirectory() -> None:
    script_path = os.path.realpath(__file__)
    script_directory = os.path.dirname(script_path)
    info.root_directory = os.path.abspath(os.path.join(script_directory, '..', '..', '..'))

def assertModulesInstalled(names: List[str]) -> None:
    not_found = []
    for name in names:
        if importlib.util.find_spec(name) is None:
            not_found.append(name)
    if len(not_found) > 0:
        logger.critical(f'Modules not found: {", ".join(not_found)}')
        exit(-1)

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
    if filepath:
        filepath = os.path.realpath(filepath)

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
    fileinfo = {}
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
        from elftools.elf.elffile import ELFFile
        from elftools.elf.dynamic import DynamicSection
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
                p = re.sub(r'\$ORIGIN(?=[^a-zA-Z0-9\s])', origin, p)
                p = re.sub(r'\${ORIGIN}', origin, p)
                p = re.sub(r'\$LIB(?=[^a-zA-Z0-9\s])', lib, p)
                p = re.sub(r'\${LIB}', lib, p)
                p = re.sub(r'\$PLATFORM(?=[^a-zA-Z0-9\s])', pl, p)
                p = re.sub(r'\${PLATFORM}', pl, p)
                return p
            for rpath in fileinfo['rpath']:
                findpaths.append(replace_rpath(rpath))
            if 'LD_LIBRARY_PATH' in os.environ:
                findpaths += os.environ['LD_LIBRARY_PATH'].split(os.pathsep)
            for runpath in fileinfo['runpath']:
                findpaths.append(replace_rpath(runpath))
            if fileinfo['bits'] == 64:
                findpaths += ['/lib64', '/usr/lib64']
            findpaths += ['/lib', '/usr/lib']
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
                logger.warn(filepath + ':')
                for l in depinfo:
                    logger.warn(f'    {l}')
    if len(not_found) > 0:
        logger.critical(f'Executables not found: {", ".join(not_found)}')
        exit(-1)

def findVSPlugins() -> List[str]:
    result = []
    plugin_dir = os.path.join(info.root_directory, 'bin', info.system.lower(), 'filter_plugins', 'vs')
    for root, dirs, files in os.walk(plugin_dir):
        for name in files:
            path = os.path.join(root, name)
            if path.lower().endswith('.dll') or (info.system == 'Linux' and path.endswith('.so')):
                loadBinaryInfo(path)
                fileinfo = info.binaries[path]
                if 'VapourSynthPluginInit' in fileinfo['exports']:
                    result.append(path)
                    depinfo = queryDependency(path)
                    if depinfo:
                        logger.warn(path + ':')
                        for l in depinfo:
                            logger.warn(f'    {l}')
    return result

def loadBinCache():
    cachepath = os.path.join(info.root_directory, 'bin_cache.json')
    if os.path.exists(cachepath):
        with open(cachepath, 'r') as f:
            info.binaries = json.loads(f.read())

def saveBinCache():
    cachepath = os.path.join(info.root_directory, 'bin_cache.json')
    with open(cachepath, 'w') as f:
        f.write(json.dumps(info.binaries))

def precheck() -> None:
    global windir
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    checkSystem()
    setRootDirectory()
    loadBinCache()

    if info.system == 'Linux':
        checkExecutables([('wine', True), ('winepath', True)])

    addPath(os.path.join(info.root_directory, 'bin', info.system.lower()))
    addLibPath(os.path.join(info.root_directory, 'bin', info.system.lower(), 'lib'))
    addPythonPath(os.path.join(info.root_directory, 'bin', info.system.lower(), 'lib', 'python'))
    addPythonPath(os.path.join(info.root_directory, 'conf', 'libraries'))

    if info.system == 'Windows':
        windir = os.environ['WINDIR']
    else:
        windir = subprocess.check_output([info.WINEPATH, '-u', r'C:\windows']).decode().strip()

    required_modules = [
        'yaml',              # PyYAML
        'pydub',             # pydub
        'pefile',            # pefile
    ]
    if info.system == 'Windows':
        required_modules += [
            'clr',           # pythonnet
        ]
    else:
        required_modules += [
            'fontconfig',    # Python-fontconfig
            'elftools',      # pyelftools
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
            ('x264_7mod_64-8bit.exe', False, 'x264_7mod'),
            ('x264_7mod_64-10bit.exe', False, 'x264_7mod_10bit'),
            ('x265-misaka-8bit.exe', False, 'x265'),
            ('x265-misaka-10bit.exe', False, 'x265_10bit'),
            ('qaac64.exe', True, 'qaac'),
        ]
    else:
        executables = [
            ('vspipe', True),
            ('ffmpeg', True),
            ('mediainfo', True),
            ('mkvmerge', True),
            ('mkvpropedit', True),
            ('x264', False),
            ('x264_7mod', False),
            ('x264_7mod-10bit', False),
            ('x265', False),
            ('qaac64.exe', True, 'qaac'),
        ]
    checkExecutables(executables)

    saveBinCache()
