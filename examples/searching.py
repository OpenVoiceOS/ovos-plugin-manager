from ovos_plugin_manager.installation import search_pip

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
('mycroft-precise', 'Mycroft Precise Wake Word Listener')
('msk', 'Mycroft Skills Kit')
('mycroft-messagebus-client', 'Mycroft Messagebus Client')
('majel', 'A front-end for Mycroft that allows you to do cool things like stream video or surf the web.')
('mycroft-tts-plugin-azure', 'A tts plugin for mycroft, using Azure Cognitive Services')
('mycroft-ekylibre-utils', 'Ekylibre set of tools for MycroftAI skills')
('rhasspy-wake-precise-hermes', '')
('lingua-franca', 'Mycroft&#39;s multilingual text parsing and formatting library')
('adapt-parser', 'A text-to-intent parsing framework.')
('aklogger', 'A generic logging package for python projects')
('HiveMind-chatroom', 'Mycroft Chatroom')
('jarbas-hive-mind-red', 'Mycroft Node Red')
('HiveMind-cli', 'Mycroft Remote Cli')
('msm', 'Mycroft Skills Manager')
('ovos-local-backend', 'mock mycroft backend')
('HiveMind-voice-sat', 'Mycroft Voice Satellite')
('mycroftapi', 'a library to communicate with Mycroft API')
('HiveMind-PtT', 'Mycroft Push to Talk Satellite')
('jarbas-tts-plugin-softcatala', 'A catalan tts plugin for mycroft')
('jarbas-tts-plugin-responsivevoice', 'ResponsiveVoice tts plugin for mycroft')
('speech2text', 'Mycroft STT engine wrappers')
('jarbas-wake-word-plugin-precise', 'A wake word plugin for mycroft')
('chatterbox-wake-word-plugin-dummy', 'A wake word plugin for mycroft')
('jarbas-wake-word-plugin-pocketsphinx', 'A wake word plugin for mycroft')
('jarbas-core', 'Jarbas fork of Mycroft Core')
('jarbas-stt-plugin-vosk', 'A vosk stt plugin for mycroft')
('jarbas-tts-plugin-cotovia', 'A galician/spanish tts plugin for mycroft')
('jarbas-tts-plugin-catotron', 'A catalan tacotron based tts plugin for mycroft')
('jarbas-stt-plugin-chromium', 'A stt plugin for mycroft using the google chrome browser api')
('jarbas-wake-word-plugin-nyumaya', 'Nyumaya wake word plugin for mycroft')
('jarbas-hive-mind', 'Mesh Networking utilities for mycroft core')
('jarbas-wake-word-plugin-snowboy', 'Snowboy wake word plugin for mycroft')
('jarbas-wake-word-plugin-vosk', 'Kaldi wake word plugin for mycroft')
('ovos-utils', 'collection of simple utilities for use across the mycroft ecosystem')
('precise-runner', 'Wrapper to use Mycroft Precise Wake Word Listener')
('ovos-skill-installer', 'Mycroft skill installer from .zip or .tar.gz urls')
"""
