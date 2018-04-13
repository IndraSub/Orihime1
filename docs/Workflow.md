# Workflow

### NOTICE

**The content of this document is outdated, please just ignore it.**

## Preload

Load current-working.txt
Load episode-metainfo by current-working.txt
Load project-configure by episode-metainfo

## Checking temporary files
1. if not exists create "episodes\temporary" directory
2. if exists prompt for choice clear temporary directory

## Checking subtitle file fonts installed
1. read subtitle fonts info
2. read font installed status
3. show install report
4. waiting user confirm

## Post-process with VapourSynth & Rip video data with x265
1. load x265coder on project-configure
2. execute misaka64.py with VSPipe
3. pipeline to x265 data with VSPipe STDOUT

## Extract & Trimmed Audio
1. by AviSynth

## Recode Audio
1. usage QAAC64 recode audio

## Merge audio & video data with MKVMerge

## Edit video metainfo with MKVPropEdit

1. setting title
2. setting track:1 name
2. setting track:2 name & language=jpn

## Mission Complete

1. through mediainfo print output video info