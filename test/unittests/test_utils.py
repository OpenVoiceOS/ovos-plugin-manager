import unittest

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
    }
}


class TestUtils(unittest.TestCase):
    def test_get_plugin_config(self):
        from ovos_plugin_manager.utils.config import get_plugin_config
        tts_config = get_plugin_config(_MOCK_CONFIG, "tts")
        stt_config = get_plugin_config(_MOCK_CONFIG, "stt")
        keyword_config = get_plugin_config(_MOCK_CONFIG, "keywords")
        tts_config_override = get_plugin_config(_MOCK_CONFIG, "tts",
                                                "tts-module")

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
        self.assertEqual(mb_to_bytes(1), 1024*1024)

# TODO: Write unit tests for classes in tts_cache
