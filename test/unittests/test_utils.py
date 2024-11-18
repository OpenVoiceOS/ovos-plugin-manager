import shutil
import unittest
from os import makedirs

from os.path import join, dirname, isfile
from copy import deepcopy, copy
from unittest.mock import patch, Mock

_MOCK_CONFIG = {
    "lang": "global",
    "tts": {
        "module": "test-tts-module",
        "tts-module": {
            "lang": "override"
        },
        "test-tts-module": {
            "model_path": "/test/path"
        }
    },
    "stt": {
        "module": "test-stt-module"
    },
    "keywords": {
        "lang": "keyword_lang"
    },
    "postag": {
        "module": "postag-module"
    },
    "segmentation": {
        "module": "wrong-module",
        "right-module": {
            "invalid": True
        }
    },
    "intentBox": {
        "segmentation": {
            "module": "right-module",
            "right-module": {
                "valid": True
            }
        }
    },
    "gui": {
        "module": "ovos-gui-plugin-shell-companion",
        "generic": {"homescreen_supported": True},
        "idle_display_skill": "skill-ovos-homescreen",
        "run_gui_file_server": False
    }
}

_MOCK_PLUGIN_CONFIG = {
    'af-ZA': [{'display_name': 'Afrikaans (South Africa)',
               'lang': 'af-ZA',
               'offline': False,
               'priority': 60}],
    'ar-AE': [{'display_name': 'Arabic (UAE)',
               'lang': 'ar-AE',
               'offline': False,
               'priority': 60}],
    'ar-BH': [{'display_name': 'Arabic (Bahrain)',
               'lang': 'ar-BH',
               'offline': False,
               'priority': 60}],
    'ar-DZ': [{'display_name': 'Arabic (Algeria)',
               'lang': 'ar-DZ',
               'offline': False,
               'priority': 60}],
    'ar-EG': [{'display_name': 'Arabic (Egypt)',
               'lang': 'ar-EG',
               'offline': False,
               'priority': 60}],
    'ar-IL': [{'display_name': 'Arabic (Israel)',
               'lang': 'ar-IL',
               'offline': False,
               'priority': 60}],
    'ar-IQ': [{'display_name': 'Arabic (Iraq)',
               'lang': 'ar-IQ',
               'offline': False,
               'priority': 60}],
    'ar-JO': [{'display_name': 'Arabic (Jordan)',
               'lang': 'ar-JO',
               'offline': False,
               'priority': 60}],
    'ar-KW': [{'display_name': 'Arabic (Kuwait)',
               'lang': 'ar-KW',
               'offline': False,
               'priority': 60}],
    'ar-LB': [{'display_name': 'Arabic (Lebanon)',
               'lang': 'ar-LB',
               'offline': False,
               'priority': 60}],
    'ar-MA': [{'display_name': 'Arabic (Morocco)',
               'lang': 'ar-MA',
               'offline': False,
               'priority': 60}],
    'ar-OM': [{'display_name': 'Arabic (Oman)',
               'lang': 'ar-OM',
               'offline': False,
               'priority': 60}],
    'ar-PS': [{'display_name': 'Arabic (Palestinian Territory)',
               'lang': 'ar-PS',
               'offline': False,
               'priority': 60}],
    'ar-QA': [{'display_name': 'Arabic (Qatar)',
               'lang': 'ar-QA',
               'offline': False,
               'priority': 60}],
    'ar-SA': [{'display_name': 'Arabic (Saudi Arabia)',
               'lang': 'ar-SA',
               'offline': False,
               'priority': 60}],
    'ar-TN': [{'display_name': 'Arabic (Tunisia)',
               'lang': 'ar-TN',
               'offline': False,
               'priority': 60}],
    'bg-BG': [{'display_name': 'Bulgarian (Bulgaria)',
               'lang': 'bg-BG',
               'offline': False,
               'priority': 60}],
    'ca-ES': [{'display_name': 'Catalan (Spain)',
               'lang': 'ca-ES',
               'offline': False,
               'priority': 60}],
    'cs-CZ': [{'display_name': 'Czech (Czech Republic)',
               'lang': 'cs-CZ',
               'offline': False,
               'priority': 60}],
    'da-DK': [{'display_name': 'Danish (Denmark)',
               'lang': 'da-DK',
               'offline': False,
               'priority': 60}],
    'de-DE': [{'display_name': 'German (Germany)',
               'lang': 'de-DE',
               'offline': False,
               'priority': 60}],
    'el-GR': [{'display_name': 'Greek (Greece)',
               'lang': 'el-GR',
               'offline': False,
               'priority': 60}],
    'en-AU': [{'display_name': 'English (Australia)',
               'lang': 'en-AU',
               'offline': False,
               'priority': 60}],
    'en-CA': [{'display_name': 'English (Canada)',
               'lang': 'en-CA',
               'offline': False,
               'priority': 60}],
    'en-GB': [{'display_name': 'English (United Kingdom)',
               'lang': 'en-GB',
               'offline': False,
               'priority': 60}],
    'en-IE': [{'display_name': 'English (Ireland)',
               'lang': 'en-IE',
               'offline': False,
               'priority': 60}],
    'en-IN': [{'display_name': 'English (India)',
               'lang': 'en-IN',
               'offline': False,
               'priority': 60}],
    'en-NZ': [{'display_name': 'English (New Zealand)',
               'lang': 'en-NZ',
               'offline': False,
               'priority': 60}],
    'en-PH': [{'display_name': 'English (Philippines)',
               'lang': 'en-PH',
               'offline': False,
               'priority': 60}],
    'en-US': [{'display_name': 'English (United States)',
               'lang': 'en-US',
               'offline': False,
               'priority': 60}],
    'en-ZA': [{'display_name': 'English (South Africa)',
               'lang': 'en-ZA',
               'offline': False,
               'priority': 60}],
    'es-AR': [{'display_name': 'Spanish (Argentina)',
               'lang': 'es-AR',
               'offline': False,
               'priority': 60}],
    'es-BO': [{'display_name': 'Spanish (Bolivia)',
               'lang': 'es-BO',
               'offline': False,
               'priority': 60}],
    'es-CL': [{'display_name': 'Spanish (Chile)',
               'lang': 'es-CL',
               'offline': False,
               'priority': 60}],
    'es-CO': [{'display_name': 'Spanish (Colombia)',
               'lang': 'es-CO',
               'offline': False,
               'priority': 60}],
    'es-CR': [{'display_name': 'Spanish (Costa Rica)',
               'lang': 'es-CR',
               'offline': False,
               'priority': 60}],
    'es-DO': [{'display_name': 'Spanish (Dominican Republic)',
               'lang': 'es-DO',
               'offline': False,
               'priority': 60}],
    'es-EC': [{'display_name': 'Spanish (Ecuador)',
               'lang': 'es-EC',
               'offline': False,
               'priority': 60}],
    'es-ES': [{'display_name': 'Spanish (Spain)',
               'lang': 'es-ES',
               'offline': False,
               'priority': 60}],
    'es-GT': [{'display_name': 'Spanish (Guatemala)',
               'lang': 'es-GT',
               'offline': False,
               'priority': 60}],
    'es-HN': [{'display_name': 'Spanish (Honduras)',
               'lang': 'es-HN',
               'offline': False,
               'priority': 60}],
    'es-MX': [{'display_name': 'Spanish (México)',
               'lang': 'es-MX',
               'offline': False,
               'priority': 60}],
    'es-NI': [{'display_name': 'Spanish (Nicaragua)',
               'lang': 'es-NI',
               'offline': False,
               'priority': 60}],
    'es-PA': [{'display_name': 'Spanish (Panamá)',
               'lang': 'es-PA',
               'offline': False,
               'priority': 60}],
    'es-PE': [{'display_name': 'Spanish (Perú)',
               'lang': 'es-PE',
               'offline': False,
               'priority': 60}],
    'es-PR': [{'display_name': 'Spanish (Puerto Rico)',
               'lang': 'es-PR',
               'offline': False,
               'priority': 60}],
    'es-PY': [{'display_name': 'Spanish (Paraguay)',
               'lang': 'es-PY',
               'offline': False,
               'priority': 60}],
    'es-SV': [{'display_name': 'Spanish (El Salvador)',
               'lang': 'es-SV',
               'offline': False,
               'priority': 60}],
    'es-US': [{'display_name': 'Spanish (United States)',
               'lang': 'es-US',
               'offline': False,
               'priority': 60}],
    'es-UY': [{'display_name': 'Spanish (Uruguay)',
               'lang': 'es-UY',
               'offline': False,
               'priority': 60}],
    'es-VE': [{'display_name': 'Spanish (Venezuela)',
               'lang': 'es-VE',
               'offline': False,
               'priority': 60}],
    'eu-ES': [{'display_name': 'Basque (Spain)',
               'lang': 'eu-ES',
               'offline': False,
               'priority': 60}],
    'fa-IR': [{'display_name': 'Farsi (Iran)',
               'lang': 'fa-IR',
               'offline': False,
               'priority': 60}],
    'fi-FI': [{'display_name': 'Finnish (Finland)',
               'lang': 'fi-FI',
               'offline': False,
               'priority': 60}],
    'fil-PH': [{'display_name': 'Filipino (Philippines)',
                'lang': 'fil-PH',
                'offline': False,
                'priority': 60}],
    'fr-FR': [{'display_name': 'French (France)',
               'lang': 'fr-FR',
               'offline': False,
               'priority': 60}],
    'gl-ES': [{'display_name': 'Galician (Spain)',
               'lang': 'gl-ES',
               'offline': False,
               'priority': 60}],
    'he-IL': [{'display_name': 'Hebrew (Israel)',
               'lang': 'he-IL',
               'offline': False,
               'priority': 60}],
    'hi-IN': [{'display_name': 'Hindi (India)',
               'lang': 'hi-IN',
               'offline': False,
               'priority': 60}],
    'hr-HR': [{'display_name': 'Croatian (Croatia)',
               'lang': 'hr_HR',
               'offline': False,
               'priority': 60}],
    'hu-HU': [{'display_name': 'Hungarian (Hungary)',
               'lang': 'hu-HU',
               'offline': False,
               'priority': 60}],
    'id-ID': [{'display_name': 'Indonesian (Indonesia)',
               'lang': 'id-ID',
               'offline': False,
               'priority': 60}],
    'is-IS': [{'display_name': 'Icelandic (Iceland)',
               'lang': 'is-IS',
               'offline': False,
               'priority': 60}],
    'it-CH': [{'display_name': 'Italian (Switzerland)',
               'lang': 'it-CH',
               'offline': False,
               'priority': 60}],
    'it-IT': [{'display_name': 'Italian (Italy)',
               'lang': 'it-IT',
               'offline': False,
               'priority': 60}],
    'ja-JP': [{'display_name': 'Japanese (Japan)',
               'lang': 'ja-JP',
               'offline': False,
               'priority': 60}],
    'ko-KR': [{'display_name': 'Korean (Korea)',
               'lang': 'ko-KR',
               'offline': False,
               'priority': 60}],
    'lt-LT': [{'display_name': 'Lithuanian (Lithuania)',
               'lang': 'lt-LT',
               'offline': False,
               'priority': 60}],
    'ms-MY': [{'display_name': 'Malaysian (Malaysia)',
               'lang': 'ms-MY',
               'offline': False,
               'priority': 60}],
    'nb-NO': [{'display_name': 'Norwegian (Norway)',
               'lang': 'nb-NO',
               'offline': False,
               'priority': 60}],
    'nl-NL': [{'display_name': 'Dutch (Netherlands)',
               'lang': 'nl-NL',
               'offline': False,
               'priority': 60}],
    'pl-PL': [{'display_name': 'Polish (Poland)',
               'lang': 'pl-PL',
               'offline': False,
               'priority': 60}],
    'pt-BR': [{'display_name': 'Portuguese (Brazil)',
               'lang': 'pt-BR',
               'offline': False,
               'priority': 60}],
    'pt-PT': [{'display_name': 'Portuguese (Portugal)',
               'lang': 'pt-PT',
               'offline': False,
               'priority': 60}],
    'ro-RO': [{'display_name': 'Romanian (Romania)',
               'lang': 'ro-RO',
               'offline': False,
               'priority': 60}],
    'ru-RU': [{'display_name': 'Russian (Russia)',
               'lang': 'ru-RU',
               'offline': False,
               'priority': 60}],
    'sk-SK': [{'display_name': 'Slovak (Slovakia)',
               'lang': 'sk-SK',
               'offline': False,
               'priority': 60}],
    'sl-SI': [{'display_name': 'Slovenian (Slovenia)',
               'lang': 'sl-SI',
               'offline': False,
               'priority': 60}],
    'sr-RS': [{'display_name': 'Serbian (Serbia)',
               'lang': 'sr-RS',
               'offline': False,
               'priority': 60}],
    'sv-SE': [{'display_name': 'Swedish (Sweden)',
               'lang': 'sv-SE',
               'offline': False,
               'priority': 60}],
    'th-TH': [{'display_name': 'Thai (Thailand)',
               'lang': 'th-TH',
               'offline': False,
               'priority': 60}],
    'tr-TR': [{'display_name': 'Turkish (Turkey)',
               'lang': 'tr-TR',
               'offline': False,
               'priority': 60}],
    'uk-UA': [{'display_name': 'Ukrainian (Ukraine)',
               'lang': 'uk-UA',
               'offline': False,
               'priority': 60}],
    'vi-VN': [{'display_name': 'Vietnamese (Viet Nam)',
               'lang': 'vi-VN',
               'offline': False,
               'priority': 60}],
    'yue-Hant-HK': [{'display_name': 'Chinese Cantonese (Hong Kong)',
                     'lang': 'yue-Hant-HK',
                     'offline': False,
                     'priority': 60}],
    'zh-Hans-CN': [{'display_name': 'Chinese Mandarin (China (Simp.))',
                    'lang': 'cmn-Hans-CN',
                    'offline': False,
                    'priority': 60}],
    'zh-Hans-HK': [{'display_name': 'Chinese Mandarin (Hong Kong SAR (Trad.))',
                    'lang': 'cmn-Hans-HK',
                    'offline': False,
                    'priority': 60}],
    'zh-Hant-TW': [{'display_name': 'Chinese Mandarin (Taiwan (Trad.))',
                    'lang': 'cmn-Hant-TW',
                    'offline': False,
                    'priority': 60}],
    'zu-ZA': [{'display_name': 'Zulu (South Africa)',
               'lang': 'zu-ZA',
               'offline': False,
               'priority': 60}]}

_MOCK_VALID_STT_PLUGINS_CONFIG = {
    'deepspeech_stream_local': [{'display_name': 'English (en-US)',
                                 'lang': 'en-US',
                                 'offline': True,
                                 'priority': 85}],
    'google_cloud_streaming': [{'display_name': 'English (Australia)',
                                'lang': 'en-AU',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Canada)',
                                'lang': 'en-CA',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (United Kingdom)',
                                'lang': 'en-GB',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Ghana)',
                                'lang': 'en-GH',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Hong Kong)',
                                'lang': 'en-HK',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Ireland)',
                                'lang': 'en-IE',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (India)',
                                'lang': 'en-IN',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Kenya)',
                                'lang': 'en-KE',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Nigeria)',
                                'lang': 'en-NG',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (New Zealand)',
                                'lang': 'en-NZ',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Philippines)',
                                'lang': 'en-PH',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Pakistan)',
                                'lang': 'en-PK',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Singapore)',
                                'lang': 'en-SG',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Tanzania)',
                                'lang': 'en-TZ',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (United States)',
                                'lang': 'en-US',
                                'offline': False,
                                'priority': 80},
                               {'display_name': 'English (South Africa)',
                                'lang': 'en-ZA',
                                'offline': False,
                                'priority': 75}],
    'ovos-stt-plugin-dummy': [],
    'ovos-stt-plugin-selene': [{'display_name': 'English (Australia)',
                                'lang': 'en-AU',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Canada)',
                                'lang': 'en-CA',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (India)',
                                'lang': 'en-IN',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Ireland)',
                                'lang': 'en-IE',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (New Zealand)',
                                'lang': 'en-NZ',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (Philippines)',
                                'lang': 'en-PH',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (South Africa)',
                                'lang': 'en-ZA',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (United Kingdom)',
                                'lang': 'en-GB',
                                'offline': False,
                                'priority': 75},
                               {'display_name': 'English (United States)',
                                'lang': 'en-US',
                                'offline': False,
                                'priority': 75}],
    'ovos-stt-plugin-vosk': [],
    'ovos-stt-plugin-vosk-streaming': []}


class TestUtils(unittest.TestCase):
    def test_plugin_types(self):
        from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
        for plug_type in PluginTypes:
            self.assertIsInstance(plug_type, PluginTypes)
            self.assertIsInstance(plug_type, str)
            # Handle plugins without associated config entrypoint
            if plug_type not in (PluginTypes.PERSONA,):
                self.assertIsInstance(PluginConfigTypes(f"{plug_type.value}.config"),
                                      PluginConfigTypes)
        for cfg_type in PluginConfigTypes:
            self.assertIsInstance(cfg_type, PluginConfigTypes)
            self.assertIsInstance(cfg_type, str)
            self.assertTrue(cfg_type.value.endswith('.config'))

    @patch("ovos_plugin_manager.utils.LOG.error")
    @patch("ovos_plugin_manager.utils._iter_entrypoints")
    def test_find_plugins(self, iter_entrypoints, log_error):
        from ovos_plugin_manager.utils import find_plugins
        good_plugin = Mock(name="working_plugin")
        bad_plugin = Mock(name="failing_plugin")
        bad_plugin.load = Mock(
            side_effect=Exception("This plugin doesn't load"))

        # Test load valid plugin
        iter_entrypoints.return_value = [good_plugin]
        valid_loaded = find_plugins()
        self.assertEqual(len(valid_loaded), 1)
        self.assertEqual(list(valid_loaded.keys())[0], good_plugin.name)
        self.assertEqual(list(valid_loaded.values())[0], good_plugin.load())
        log_error.assert_not_called()

        # Test load with invalid plugin
        iter_entrypoints.return_value.append(bad_plugin)
        with_invalid_loaded = find_plugins()
        self.assertEqual(with_invalid_loaded.keys(), valid_loaded.keys())
        log_error.assert_called_once()

        # Test error not re-logged
        with_invalid_reloaded = find_plugins()
        self.assertEqual(with_invalid_reloaded.keys(),
                         with_invalid_loaded.keys())
        log_error.assert_called_once()

        # TODO: Test loading by plugin type

    def test_load_plugin(self):
        from ovos_plugin_manager.utils import load_plugin
        # TODO

    def test_normalize_lang(self):
        from ovos_plugin_manager.utils import normalize_lang
        # TODO

    def test_read_write_stream(self):
        from ovos_plugin_manager.utils import ReadWriteStream
        # TODO


class TestConfigUtils(unittest.TestCase):
    @patch("ovos_plugin_manager.utils.config.Configuration")
    def test_get_plugin_config(self, config):
        config.return_value = _MOCK_CONFIG
        from ovos_plugin_manager.utils.config import get_plugin_config
        start_config = copy(_MOCK_CONFIG)
        tts_config = get_plugin_config(_MOCK_CONFIG, "tts")
        stt_config = get_plugin_config(_MOCK_CONFIG, "stt")
        keyword_config = get_plugin_config(_MOCK_CONFIG, "keywords")
        tts_config_override = get_plugin_config(_MOCK_CONFIG, "tts",
                                                "tts-module")
        seg_config = get_plugin_config(_MOCK_CONFIG, "segmentation")
        pos_config = get_plugin_config(_MOCK_CONFIG, "postag")
        gui_config = get_plugin_config(_MOCK_CONFIG, "gui")

        self.assertEqual(tts_config,
                         {"lang": "global",
                          "module": "test-tts-module",
                          "model_path": "/test/path"})

        self.assertEqual(stt_config,
                         {"lang": "global",
                          "module": "test-stt-module"})

        self.assertEqual(keyword_config,
                         {"lang": "keyword_lang"})

        self.assertEqual(tts_config_override,
                         {"lang": "override",
                          "module": "tts-module"})

        self.assertEqual(pos_config,
                         {"lang": "global",
                          "module": "postag-module"})

        self.assertEqual(seg_config,
                         {"lang": "global",
                          "module": "right-module",
                          "valid": True})

        self.assertEqual(gui_config,
                         {"module": "ovos-gui-plugin-shell-companion",
                          "idle_display_skill": "skill-ovos-homescreen",
                          "run_gui_file_server": False
                          })

        # Test for same behavior with global config
        self.assertEqual(tts_config, get_plugin_config(section="tts"))
        self.assertEqual(stt_config, get_plugin_config(section="stt"))
        self.assertEqual(keyword_config, get_plugin_config(section="keywords"))
        self.assertEqual(pos_config, get_plugin_config(section="postag"))
        self.assertEqual(seg_config, get_plugin_config(section="segmentation"))
        self.assertEqual(gui_config, get_plugin_config(section="gui"))

        # Test TTS config with plugin `lang` override
        config = {
            "lang": "en-US",
            "tts": {
                "module": "ovos_tts_plugin_espeakng",
                "ovos_tts_plugin_espeakng": {
                  "lang": "de-DE",
                  "voice": "german-mbrola-5",
                  "speed": "135",
                  "amplitude": "80",
                  "pitch": "20"
                }
            }
        }
        tts_config = get_plugin_config(config, "tts")
        self.assertEqual(tts_config['lang'], 'de-DE')
        self.assertEqual(tts_config['module'], 'ovos_tts_plugin_espeakng')
        self.assertEqual(tts_config['voice'], 'german-mbrola-5')
        self.assertNotIn("ovos_tts_plugin_espeakng", tts_config)

        # Test PHAL with no configuration
        phal_config = get_plugin_config(config, "PHAL")
        self.assertEqual(set(phal_config.keys()), config.keys())
        phal_config = get_plugin_config(config, "PHAL", "test_plugin")
        self.assertEqual(phal_config, {"module": "test_plugin",
                                       "lang": config["lang"]})

        self.assertEqual(_MOCK_CONFIG, start_config)

    def test_get_valid_plugin_configs(self):
        from ovos_plugin_manager.utils.config import get_valid_plugin_configs
        valid_en_us = get_valid_plugin_configs(_MOCK_PLUGIN_CONFIG,
                                               'en-US', False)
        self.assertEqual(len(valid_en_us), 1)
        valid_en = get_valid_plugin_configs(_MOCK_PLUGIN_CONFIG, 'en-US', True)

        self.assertEqual(len(valid_en), 9)
        invalid_lang = get_valid_plugin_configs(_MOCK_PLUGIN_CONFIG, 'en-ZZ',
                                                False)
        self.assertIsInstance(invalid_lang, list)
        self.assertEqual(len(invalid_lang), 0)

    def test_sort_plugin_configs(self):
        from ovos_plugin_manager.utils.config import sort_plugin_configs
        sorted_configs = sort_plugin_configs(_MOCK_VALID_STT_PLUGINS_CONFIG)

        self.assertEqual(sorted_configs['google_cloud_streaming'][-1],
                         {'display_name': 'English (United States)',
                          'lang': 'en-US',
                          'offline': False,
                          'priority': 80}
                         )

    def test_load_plugin_configs(self):
        from ovos_plugin_manager.utils.config import load_plugin_configs
        # TODO

    def test_load_configs_for_plugin_type(self):
        from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
        # TODO

    def test_get_plugin_supported_languages(self):
        from ovos_plugin_manager.utils.config import get_plugin_supported_languages
        # TODO

    def test_get_plugin_language_configs(self):
        from ovos_plugin_manager.utils.config import get_plugin_language_configs
        # TODO


class TestTTSCacheUtils(unittest.TestCase):
    def test_hash_sentence(self):
        from ovos_plugin_manager.utils.tts_cache import hash_sentence
        test_sentence = "This is a test. Only UTF-8 Characters."
        hashed = hash_sentence(test_sentence)

        # Test hashes are equal
        self.assertEqual(hashed, hash_sentence(test_sentence))

        # Test hash of utf-16 characters
        test_sentence = "你们如何"
        hashed = hash_sentence(test_sentence)
        self.assertIsInstance(hashed, str)

    def test_hash_from_path(self):
        from ovos_plugin_manager.utils.tts_cache import hash_from_path
        from pathlib import Path
        from os.path import splitext, basename
        p = Path(__file__)
        self.assertEqual(hash_from_path(p), splitext(basename(__file__))[0])

    def test_mb_to_bytes(self):
        from ovos_plugin_manager.utils.tts_cache import mb_to_bytes
        self.assertEqual(mb_to_bytes(1), 1024 * 1024)

    def test_get_cache_entries(self):
        from ovos_plugin_manager.utils.tts_cache import _get_cache_entries
        # TODO

    def test_delete_oldest(self):
        from ovos_plugin_manager.utils.tts_cache import _delete_oldest
        # TODO

    def test_curate_cache(self):
        from ovos_plugin_manager.utils.tts_cache import curate_cache
        test_dir = join(dirname(__file__), "mock_cache")
        test_file = join(test_dir, "file.bin")
        # curate cache directory not found
        with self.assertRaises(NotADirectoryError):
            curate_cache(test_dir)

        makedirs(test_dir, exist_ok=True)
        with open(test_file, 'wb+') as f:
            f.write(b'12345678')

        # curate cache passed file
        with self.assertRaises(NotADirectoryError):
            curate_cache(test_file)

        # curate cache sufficient free percent
        files = curate_cache(test_dir, 0.0, 10000000.0)
        self.assertEqual(files, list())

        # Curate cache sufficient free disk
        files = curate_cache(test_dir, 100.0, 0.0)
        self.assertEqual(files, list())

        # Curate cache remove files
        self.assertTrue(isfile(test_file))
        files = curate_cache(test_dir, 100.0, 10000000.0)
        self.assertEqual(files, [test_file])
        self.assertFalse(isfile(test_file))

        shutil.rmtree(test_dir)

    def test_audio_file(self):
        from ovos_plugin_manager.utils.tts_cache import AudioFile
        # TODO

    def test_phoneme_file(self):
        from ovos_plugin_manager.utils.tts_cache import PhonemeFile
        # TODO

    def test_tts_cache(self):
        from ovos_plugin_manager.utils.tts_cache import TextToSpeechCache
        # TODO


class TestUiUtils(unittest.TestCase):
    def test_hash_dict(self):
        from ovos_plugin_manager.utils.ui import hash_dict
        self.assertIsInstance(hash_dict({'test': 3,
                                         'key': False,
                                         'third': None}), str)

    def test_plugin_ui_helper_migrate_old_cfg(self):
        from ovos_plugin_manager.utils.ui import PluginUIHelper
        old_cfg = _MOCK_VALID_STT_PLUGINS_CONFIG['deepspeech_stream_local'][0]
        new_cfg = PluginUIHelper._migrate_old_cfg(old_cfg)
        self.assertEqual(new_cfg, {'lang': 'en-US',
                                   'meta': {
                                       'display_name': 'English (en-US)',
                                       'offline': True,
                                       'priority': 85
                                   }})
        self.assertEqual(new_cfg, old_cfg)

        new_new_cfg = PluginUIHelper._migrate_old_cfg(new_cfg)
        self.assertEqual(new_cfg, new_new_cfg)

    @patch("ovos_plugin_manager.stt.get_stt_lang_configs")
    def test_plugin_ui_helper_get_config_options_STT(self, get_stt_lang_configs):
        get_stt_lang_configs.return_value = deepcopy(_MOCK_VALID_STT_PLUGINS_CONFIG)
        import importlib
        import ovos_plugin_manager.utils.ui
        importlib.reload(ovos_plugin_manager.utils.ui)
        from ovos_plugin_manager.utils.ui import PluginUIHelper, PluginTypes, \
            hash_dict

        flat_valid_configs = list()
        [flat_valid_configs.extend(cfg) for
         cfg in _MOCK_VALID_STT_PLUGINS_CONFIG.values()]

        self.assertFalse(PluginUIHelper._stt_init)
        self.assertFalse(PluginUIHelper._tts_init)

        # Test simple language no locale
        stt_opts = PluginUIHelper.get_config_options('en', PluginTypes.STT)

        # Check class variables
        self.assertTrue(PluginUIHelper._stt_init)
        self.assertFalse(PluginUIHelper._tts_init)

        # Validate returned list
        self.assertIsInstance(stt_opts, list)
        self.assertEqual(len(stt_opts), len(flat_valid_configs))
        for opt in stt_opts:
            self.assertEqual(set(opt.keys()), {'plugin_name', 'display_name',
                                               'offline', 'lang', 'engine',
                                               'plugin_type'})
            self.assertIsInstance(PluginUIHelper._stt_opts[hash_dict(opt)],
                                  dict)

        # Test blacklisted and preferred plugins
        stt_opts = PluginUIHelper.get_config_options(
            'en', PluginTypes.STT, ['ovos-stt-plugin-selene'],
            ['deepspeech_stream_local'])
        self.assertEqual(stt_opts[0]['plugin_name'], 'Deepspeech Stream Local')
        for opt in stt_opts:
            self.assertNotEqual(opt['plugin_name'].lower(),
                                "ovos stt plugin selene")

        # Test Max Options
        stt_opts = PluginUIHelper.get_config_options('en', PluginTypes.STT,
                                                     max_opts=5)
        self.assertEqual(len(stt_opts), 5)

    @patch("ovos_plugin_manager.stt.get_stt_lang_configs")
    def test_plugin_ui_helper_get_plugin_options_STT(self, get_stt_lang_configs):
        get_stt_lang_configs.return_value = deepcopy(_MOCK_VALID_STT_PLUGINS_CONFIG)
        import importlib
        import ovos_plugin_manager.utils.ui
        importlib.reload(ovos_plugin_manager.utils.ui)
        from ovos_plugin_manager.utils.ui import PluginUIHelper, PluginTypes

        stt_plugins = PluginUIHelper.get_plugin_options('en', PluginTypes.STT)
        self.assertIsInstance(stt_plugins, list)
        self.assertEqual(len(stt_plugins),
                         len([p for p in _MOCK_VALID_STT_PLUGINS_CONFIG.values()
                              if p]))
        for plug in stt_plugins:
            self.assertEqual(set(plug.keys()), {'engine', 'plugin_name',
                                                'supports_offline_mode',
                                                'supports_online_mode',
                                                'options'})
            self.assertIsInstance(plug['engine'], str)
            self.assertIsInstance(plug['plugin_name'], str)
            self.assertIsInstance(plug['supports_offline_mode'], bool)
            self.assertIsInstance(plug['supports_online_mode'], bool)
            self.assertIsInstance(plug['options'], list)
            for opt in plug['options']:
                self.assertIsInstance(opt, dict)
                self.assertEqual(set(opt.keys()),
                                 {'plugin_name', 'display_name', 'offline',
                                  'lang', 'engine', 'plugin_type'})

    @patch("ovos_plugin_manager.stt.get_stt_lang_configs")
    def test_plugin_ui_helper_get_extra_setup_STT(self, get_stt_lang_configs):
        get_stt_lang_configs.return_value = deepcopy(_MOCK_VALID_STT_PLUGINS_CONFIG)
        import importlib
        import ovos_plugin_manager.utils.ui
        importlib.reload(ovos_plugin_manager.utils.ui)
        from ovos_plugin_manager.utils.ui import PluginUIHelper, PluginTypes

        opts = PluginUIHelper.get_plugin_options('en', PluginTypes.STT)
        for opt in opts:
            self.assertIsInstance(
                PluginUIHelper.get_extra_setup(opt, PluginTypes.STT), dict)

    @patch("ovos_plugin_manager.stt.get_stt_lang_configs")
    def test_plugin_ui_helper_config2option_STT(self, get_stt_lang_configs):
        get_stt_lang_configs.return_value = deepcopy(_MOCK_VALID_STT_PLUGINS_CONFIG)
        import importlib
        import ovos_plugin_manager.utils.ui
        importlib.reload(ovos_plugin_manager.utils.ui)
        from ovos_plugin_manager.utils.ui import PluginUIHelper, PluginTypes, \
            hash_dict

        old_plugin_config = {'display_name': 'English (United States)',
                             'lang': 'en-US',
                             'offline': False,
                             'priority': 75,
                             "module": "google_cloud_streaming"}
        plugin_config = {'lang': 'en-US',
                         'module': 'google_cloud_streaming',
                         'meta': {'display_name': 'English (United States)',
                                  'offline': False,
                                  'priority': 75}}

        # Test config2option with migration
        old_opt = PluginUIHelper.config2option(deepcopy(old_plugin_config),
                                               PluginTypes.STT, 'en')
        self.assertIsInstance(PluginUIHelper._stt_opts[hash_dict(old_opt)],
                              dict)
        self.assertEqual(set(old_opt.keys()), {'plugin_name', 'display_name',
                                               'offline', 'lang', 'engine',
                                               'plugin_type'})
        # Migrated configuration
        self.assertEqual(plugin_config,
                         PluginUIHelper._stt_opts[hash_dict(old_opt)])

        # Test config2option without migration
        new_opt = PluginUIHelper.config2option(deepcopy(plugin_config),
                                               PluginTypes.STT, 'en')
        self.assertIsInstance(PluginUIHelper._stt_opts[hash_dict(old_opt)],
                              dict)
        self.assertIsInstance(PluginUIHelper._stt_opts[hash_dict(new_opt)],
                              dict)
        self.assertEqual(old_opt, new_opt)
        self.assertEqual(plugin_config,
                         PluginUIHelper._stt_opts[hash_dict(new_opt)])

    @patch("ovos_plugin_manager.stt.get_stt_lang_configs")
    def test_plugin_ui_helper_option2config_STT(self, get_stt_lang_configs):
        get_stt_lang_configs.return_value = deepcopy(_MOCK_VALID_STT_PLUGINS_CONFIG)
        import importlib
        import ovos_plugin_manager.utils.ui
        importlib.reload(ovos_plugin_manager.utils.ui)
        from ovos_plugin_manager.utils.ui import PluginUIHelper, PluginTypes, \
            hash_dict

        valid_opt = {'plugin_name': 'Deepspeech Stream Local',
                     'display_name': 'English (en-US)',
                     'offline': True,
                     'lang': 'en',
                     'engine': 'deepspeech_stream_local',
                     'plugin_type': PluginTypes.STT}

        # Init STT configurations
        opts = PluginUIHelper.get_config_options('en', PluginTypes.STT)
        self.assertIn(valid_opt, opts)
        self.assertTrue(PluginUIHelper._stt_init)
        self.assertIsNotNone(PluginUIHelper._stt_opts)

        # Validate config
        self.assertIsInstance(PluginUIHelper._stt_opts[hash_dict(valid_opt)],
                              dict)

        # Get config out
        config = PluginUIHelper.option2config(valid_opt, PluginTypes.STT)
        self.assertEqual(set(config.keys()), {'lang', 'meta', 'module'})

    # TODO: Duplicate STT tests for TTS
