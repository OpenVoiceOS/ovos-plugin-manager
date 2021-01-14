from ovos_plugin_manager.utils import search_pip

packages = search_pip("mycroft-tts-plugin")
"""
[('mycroft-tts-plugin-azure',
  'A tts plugin for mycroft, using Azure Cognitive Services')]
"""

packages = search_pip("jarbas-tts-plugin")
"""
[('jarbas-tts-plugin-cotovia', 'A galician/spanish tts plugin for mycroft'),
 ('jarbas-tts-plugin-voicerss', 'A catalan tts plugin for mycroft'),
 ('jarbas-tts-plugin-softcatala', 'A catalan tts plugin for mycroft'),
 ('jarbas-tts-plugin-responsivevoice', 'ResponsiveVoice tts plugin for mycroft'),
 ('jarbas-tts-plugin-catotron', 'A catalan tacotron based tts plugin for mycroft')]
"""

packages = search_pip("mycroft")
"""
[('mycroft-precise', 'Mycroft Precise Wake Word Listener'),
 ('mycroft-messagebus-client', 'Mycroft Messagebus Client'),
 ('mycroft-tts-plugin-azure', 'A tts plugin for mycroft, using Azure Cognitive Services'),
 ('mycroft-ekylibre-utils', 'Ekylibre set of tools for MycroftAI skills'),
 ('mycroftapi', 'a library to communicate with Mycroft API')]
"""

packages = search_pip("mycroft", strict=False)
"""
[('mycroft-precise', 'Mycroft Precise Wake Word Listener'),
 ('msk', 'Mycroft Skills Kit'),
 ('mycroft-messagebus-client', 'Mycroft Messagebus Client'),
 ('majel', 'A front-end for Mycroft that allows you to do cool things like stream video or surf the web.'),
 ('mycroft-tts-plugin-azure', 'A tts plugin for mycroft, using Azure  Cognitive Services'),
 ('mycroft-ekylibre-utils', 'Ekylibre set of tools for MycroftAI skills'),
 ('rhasspy-wake-precise-hermes', ''),
 ('lingua-franca', 'Mycroft&#39;s multilingual text parsing and formatting library'),
 ('adapt-parser', 'A text-to-intent parsing framework.'),
 ('aklogger', 'A generic logging package for python projects'),
 ('HiveMind-chatroom', 'Mycroft Chatroom'),
 ('jarbas-hive-mind-red', 'Mycroft Node Red'),
 ('HiveMind-cli', 'Mycroft Remote Cli'),
 ('msm', 'Mycroft Skills Manager'),
 ('ovos-local-backend', 'mock mycroft backend'),
 ('HiveMind-voice-sat', 'Mycroft Voice Satellite'),
 ('mycroftapi', 'a library to communicate with Mycroft API'),
 ('HiveMind-PtT', 'Mycroft Push to Talk Satellite')]
"""