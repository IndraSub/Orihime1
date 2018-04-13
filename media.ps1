Import-Module '.\bin\powershell-modules\kit.psm1'
Import-Module '.\bin\powershell-modules\Precheck-ASS-Fonts\Precheck-ASS-Fonts.psm1'

AssertModulesInstalled 'Use-RawPipeline', 'powershell-yaml', 'PSStringTemplate'

$env:Path = "$env:Path;$PSScriptRoot\bin"

$content = Get-WorkingContent
$temporary = "$(Get-WorkingDirectory)\temporary"

function MissionReport([string] $title, [string] $output){
    Write-EventName 'Mission Report'

    $working_directory = Resolve-Path -Relative (Get-WorkingDirectory)
    $report = [PSCustomObject] @{
        "Title" = $title
        "Temporary Files" = "$working_directory\temporary"
        "Quality" = $content['quality']
        "Source" = "$working_directory\$($content['source']['filename'])"
        "Output" = "$working_directory\$output"
    }

    $report | Format-List

    $message = 'Type your decision:'
    $choices = @(@('&Confirm', 'Confirm'), @('E&xit', 'Exit'))
    $answer = Choices $null $message $choices 1
    switch ($answer){
        1{ exit }
    }
}

function PrecleanTemporaryFiles(){
    Write-EventName 'Checking temporary files'
    $directoryInfo = Get-ChildItem $temporary | Measure-Object
    if ($directoryInfo.count -eq 0){
        $caption = 'Directory is clean.'
        Write-Output $caption
        New-Item -Force -Path $temporary -ItemType Directory | Out-Null
    } else {
        $answer = 0
        $caption = 'Temporary files exist, the previous task may not finished normally. Do you want to clear them?'
        $message = 'Type your decision:'
        $choices = @(@('&Confirm', 'Confirm'), @('E&xit', 'Exit'))
        $answer = Choices $caption $message $choices 1
        switch ($answer){
            0{
                Remove-Item -Force -Path $temporary -Recurse
                New-Item -Force -Path $temporary -ItemType Directory | Out-Null
            }
            1{ exit }
        }
    }
}

function PrecheckSubtitle(){
    if ($content['source']['subtitle'] -eq $null){ return }
    Write-EventName 'Checking if all fonts are installed'
    $subtitle = "$(Get-WorkingDirectory)\$($content['source']['subtitle']['filename'])"
    Write-ASSFontsInstalled $subtitle
    $caption = 'Please make sure that all fonts are installed'
    $message = 'Type your decision:'
    $choices = @(@('&Confirm', 'Confirm'), @('E&xit', 'Exit'))
    $answer = Choices $caption $message $choices 1
    switch ($answer){
        1{ exit }
    }
}

function PostProcessVideo([string] $output){
    Write-EventName 'Post-process with VapourSynth & Rip video data with x265'
    $vapoursynth_pipeline = @('--y4m', '--arg', "current_working=$(Get-CurrentWorking)", '.\conf\misaka64.py', '-') | FlattenArray
    $encoder_binary = $content['project']['encoder_binary']
    $encoder_params = $content['project']['encoder_params'] -split '\n' -split ' '
    if ($content['project']['encoder'] -eq 'x264'){
        $encoder = @('-', '--demuxer', 'y4m', $encoder_params, '--output', $output) | FlattenArray
    } elseif ($content['project']['encoder'] -eq 'x265'){
        $encoder = @('--y4m', $encoder_params, '--output', $output, '-') | FlattenArray
    } else {
        Write-Output "Encoder $content['project']['encoder'] is not supported, only support x264 and x265."
        exit
    }
    Invoke-NativeCommand -FilePath '.\bin\vapoursynth\vspipe.exe' -ArgumentList $vapoursynth_pipeline | `
 Invoke-NativeCommand -FilePath $encoder_binary -ArgumentList $encoder | `
 Receive-RawPipeline
    AssertFileWithExit $output
}

function BuildTrimmedScript($frames){
    $trimmedCode = 'last'
    if ($frames.Count -gt 0){
        $trimmedCode = ($frames | ForEach-Object { "Trim($($_[0]), $($_[1]))" }) -join ' + '
    }
    $parameters = @{
        LSMASHSource64PluginPath = "$PSScriptRoot\bin\filter_plugins\avs\LSMASHSource64.dll";
        SourceFile = "$(Resolve-Path (Get-WorkingDirectory))\$($content['source']['filename'])";
        TrimmedCode = $trimmedCode;
    }
    Push-Location $temporary
    'LSMASHSource64PluginPath', 'SourceFile' | ForEach-Object { $parameters[$_] = Resolve-Path -Relative $parameters[$_]; }
    Pop-Location
    Invoke-StringTemplate -Definition $input -Parameters $parameters
}

function ExtractTrimmedAudio([string] $output){
    Write-EventName 'Extract trimmed audio data to PCM format with Avisynth'

    $frames = $content['source']['trim_frames']
    $template = '.\conf\misaka64.tpl.avs'
    $script = "$temporary\audio-trimmed.avs"
    Get-Content -Raw $template | BuildTrimmedScript $frames | Set-Content $script

    $encoder = @('-hide_banner', '-y', '-i', $script, '-vn', '-acodec', 'copy', $output)
    Invoke-NativeCommand -FilePath 'ffmpeg' -ArgumentList $encoder | Receive-RawPipeline
    AssertFileWithExit $output
}

function RecodeAudio([string] $trimmedAudio, [string] $recodedAudio){
    Write-EventName 'Recode audio data to AAC format with QAAC'
    $decoder = @('-hide_banner', '-i', $trimmedAudio, '-f', 'wav', '-vn', '-')
    $encoder = @('--tvbr', 127, '--quality', 2, '--ignorelength', '-o', $recodedAudio, '-')
    Invoke-NativeCommand -FilePath 'ffmpeg' -ArgumentList $decoder | `
 Invoke-NativeCommand -FilePath 'qaac64' -ArgumentList $encoder | `
 Receive-RawPipeline
    AssertFileWithExit $recodedAudio
}

function MKVMerge([string] $output, [string] $encodedAudio, [string] $encodedVideo, [string] $title){
    Write-EventName 'Merge audio & video data with MKVMerge'
    $merge = @('-o', $output, $encodedVideo, $encodedAudio)
    Invoke-NativeCommand -FilePath 'mkvmerge' -ArgumentList $merge | Receive-RawPipeline
    AssertFileWithExit $output
}

function MKVMetainfo([string] $output, [string] $title){
    Write-EventName 'Edit video metainfo with MKVPropEdit'
    $props = @(
        $output
        '--edit', 'info', '--set', "title=${title}"
        '--edit', 'track:1', '--set', "name=${title}"
        '--edit', 'track:2', '--set', "name=${title}", '--set', 'language=jpn'
    )
    Invoke-NativeCommand -FilePath 'mkvpropedit' -ArgumentList $props | Receive-RawPipeline
    AssertFileWithExit $output
}

function CleanTemporaryFiles(){
    Write-EventName 'Clean Temporary Files'
    $caption = 'Processing flow completed, you may want to take a backup of mission temporary files.'
    $message = 'Type your decision:'
    $choices = @(@('&Clear', 'Clear all temporary files'), @('&Reserve', 'Reserve'))
    $answer = Choices $caption $message $choices 1
    switch ($answer){
        0{
            Remove-Item -Force -Path $temporary -Recurse
            New-Item -Force -Path $temporary -ItemType Directory | Out-Null
        }
        1{}
    }
}

function MissionComplete($output){
    Write-EventName 'Mission Complete'
    Invoke-NativeCommand -FilePath 'mediainfo' -ArgumentList $output | Receive-RawPipeline
}

function Main(){
    $title = Invoke-StringTemplate -Definition $content['title'] -Parameters $content
    $output = Invoke-StringTemplate -Definition $content['output']['filename'] -Parameters $content

    MissionReport $title $output $temporary
    PrecleanTemporaryFiles
    PrecheckSubtitle

    $output = "$(Get-WorkingDirectory)\$output"
    $encodedVideo = "$temporary\video-encoded.mp4"
    $trimmedAudio = "$temporary\audio-trimmed.wav"
    $encodedAudio = "$temporary\audio-encoded.m4a"

    PostProcessVideo $encodedVideo
    ExtractTrimmedAudio $trimmedAudio
    RecodeAudio $trimmedAudio $encodedAudio
    MKVMerge $output $encodedAudio $encodedVideo
    MKVMetainfo $output $title
    CleanTemporaryFiles
    MissionComplete $output
}

Main
