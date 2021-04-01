"""
NOTES

this module is meant to enable usage of mycroft plugins inside and outside
mycroft, importing from here will make things work as planned in mycroft,
but if outside mycroft things will still work

The main use case is for plugins to be used across different projects

## Differences from upstream

TTS:
- added automatic guessing of phonemes/visime calculation, enabling mouth
movements for all TTS engines (only mimic implements this in upstream)
- playback start call has been omitted and moved to init method
- init is called by mycroft, but non mycroft usage wont call it
- outside mycroft the enclosure is not set, bus is dummy and playback thread is not used
- playback queue is not wanted when some module is calling get_tts (which is the correct usage)
- if playback was started on init then python scripts would never stop

    # assuming they could even be imported in other module...
    from mycroft.tts import TTSFactory
    engine = TTSFactory.create()
    engine.get_tts("hello world", "hello_world." + engine.audio_ext)
    engine.playback.stop() # if you dont call this it will hang here forever
"""