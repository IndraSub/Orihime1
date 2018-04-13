SetMemoryMax(2048)
LoadPlugin("<LSMASHSource64PluginPath>")

Source = "<SourceFile>"

VideoSource = LWLibavVideoSource(Source, stream_index=-1)
AudioSource = LWLibavAudioSource(Source, stream_index=1, av_sync=true)
AudioDub(VideoSource, AudioSource)

src = <TrimmedCode>
KillVideo(src)
src