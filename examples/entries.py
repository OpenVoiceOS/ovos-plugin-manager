from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin
from ovos_plugin_manager.installation import search_pip

# installed
p = OpenVoiceOSPlugin.from_name("cotovia_tts_plug")
print(p.json)
"""
{'class': 'CotoviaTTSPlugin',
 'description': 'Interface to cotovia TTS.',
 'human_name': 'Cotovia TTS Plugin',
 'is_installed': True,
 'module_name': 'ovos_tts_plugin_cotovia',
 'name': 'cotovia_tts_plug',
 'package_name': None,
 'plugin_type': <PluginTypes.TTS: 'mycroft.plugin.tts'>,
 'url': None}
"""

for pkg in search_pip("mycroft-tts-plugin"):
    data = {"description": pkg[1], "package_name": pkg[0]}
    p = OpenVoiceOSPlugin(data)
    print(p.json)
"""
{'class': None,
 'description': 'A tts plugin for mycroft, using Azure Cognitive Services',
 'human_name': 'Mycroft TTS Plugin Azure',
 'is_installed': False,
 'module_name': None,
 'name': None,
 'package_name': 'mycroft-tts-plugin-azure',
 'plugin_type': <PluginTypes.TTS: 'mycroft.plugin.tts'>,
 'url': None}
"""