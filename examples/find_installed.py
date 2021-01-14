from ovos_plugin_manager.tts import find_tts_plugins
from ovos_plugin_manager.stt import find_stt_plugins
from ovos_plugin_manager import find_plugins, PluginTypes

for p in find_plugins():
    print("PLUGIN:", p)

for p in find_plugins(plug_type=PluginTypes.WAKEWORD):
    print("WAKE WORD PLUGIN:", p)

for p in find_tts_plugins():
    print("TTS PLUGIN:", p)

for p in find_stt_plugins():
    print("STT PLUGIN:", p)
