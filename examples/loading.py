from ovos_plugin_manager import load_plugin
from ovos_plugin_manager.tts import load_tts_plugin
from ovos_plugin_manager.stt import load_stt_plugin

engine = load_tts_plugin("cotovia_tts_plug")
print(engine.__name__)  # CotoviaTTSPlugin

engine = load_stt_plugin("chromium_stt_plug")
print(engine.__name__)  # ChromiumSTT

engine = load_plugin("jarbas_precise_ww_plug")
print(engine.__name__)  # PreciseHotwordPlugin

# using a plugin

engine = load_tts_plugin("google_tts_plug")
print(engine.__name__)  # gTTSPlugin

tts = engine(lang="en-us", config={})
tts.get_tts("hello world", "tts.mp3")
# if you dont call this it will hang here forever
tts.playback.stop()
