import unittest
from unittest.mock import patch, MagicMock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


# ---------------------------------------------------------------------------
# Concrete implementations for abstract classes
# ---------------------------------------------------------------------------

class _ConcreteIntentTransformer:
    from ovos_plugin_manager.templates.transformers import IntentTransformer as _Base

    class _Impl(_Base):
        def transform(self, intent):
            """
            Return the provided intent unchanged.
            
            Parameters:
                intent: The intent object to pass through (for example, an IntentHandlerMatch).
            
            Returns:
                The same `intent` object that was passed in.
            """
            return intent


_ConcreteIntentTransformer = _ConcreteIntentTransformer._Impl


class _ConcreteAudioLangDetector:
    from ovos_plugin_manager.templates.transformers import AudioLanguageDetector as _Base

    class _Impl(_Base):
        def detect(self, audio_data, valid_langs=None):
            """
            Detect the spoken language in the provided audio.
            
            Parameters:
                audio_data: Audio payload to analyze (raw bytes, bytearray, or audio buffer).
                valid_langs (Optional[Iterable[str]]): Optional sequence of language tags to restrict detection.
            
            Returns:
                tuple: A pair `(language_code, probability)` where `language_code` is the detected BCP-47 tag (e.g., "en-US") and `probability` is a float between 0 and 1 indicating confidence.
            """
            return "en-US", 0.99


_ConcreteAudioLangDetector = _ConcreteAudioLangDetector._Impl


# ---------------------------------------------------------------------------
# UtteranceTransformer
# ---------------------------------------------------------------------------

class TestUtteranceTransformer(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init_defaults(self, _):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        t = UtteranceTransformer("my-transformer")
        self.assertEqual(t.name, "my-transformer")
        self.assertEqual(t.priority, 50)
        self.assertEqual(t.config, {})
        self.assertIsNone(t.bus)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init_custom_priority_and_config(self, _):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        t = UtteranceTransformer("t", priority=10, config={"key": "val"})
        self.assertEqual(t.priority, 10)
        self.assertEqual(t.config, {"key": "val"})

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_identity(self, _):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        t = UtteranceTransformer("t")
        utterances = ["hello world"]
        result, ctx = t.transform(utterances, context={"lang": "en"})
        self.assertEqual(result, utterances)
        self.assertIsInstance(ctx, dict)

    @patch("ovos_plugin_manager.templates.transformers.get_mycroft_bus")
    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_bind(self, _, mock_bus):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        fake_bus = MagicMock()
        mock_bus.return_value = fake_bus
        t = UtteranceTransformer("t")
        t.bind()
        self.assertIs(t.bus, fake_bus)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_bind_explicit_bus(self, _):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        explicit_bus = MagicMock()
        t = UtteranceTransformer("t")
        t.bind(explicit_bus)
        self.assertIs(t.bus, explicit_bus)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_default_shutdown(self, _):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        UtteranceTransformer("t").default_shutdown()  # must not raise


# ---------------------------------------------------------------------------
# MetadataTransformer
# ---------------------------------------------------------------------------

class TestMetadataTransformer(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_identity(self, _):
        from ovos_plugin_manager.templates.transformers import MetadataTransformer
        t = MetadataTransformer("meta")
        ctx = {"key": "value"}
        result = t.transform(ctx)
        self.assertEqual(result, ctx)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_empty_context(self, _):
        from ovos_plugin_manager.templates.transformers import MetadataTransformer
        t = MetadataTransformer("meta")
        result = t.transform()
        self.assertIsInstance(result, dict)


# ---------------------------------------------------------------------------
# IntentTransformer
# ---------------------------------------------------------------------------

class TestIntentTransformer(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init(self, _):
        t = _ConcreteIntentTransformer("intent-t", priority=30)
        self.assertEqual(t.name, "intent-t")
        self.assertEqual(t.priority, 30)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_passthrough(self, _):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        t = _ConcreteIntentTransformer("intent-t")
        intent = IntentHandlerMatch(match_type="test", match_data={"k": "v"})
        result = t.transform(intent)
        self.assertIs(result, intent)


# ---------------------------------------------------------------------------
# AudioTransformer
# ---------------------------------------------------------------------------

class TestAudioTransformer(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init_defaults(self, _):
        from ovos_plugin_manager.templates.transformers import AudioTransformer
        t = AudioTransformer("audio-t")
        self.assertEqual(t.name, "audio-t")
        self.assertEqual(t.sample_rate, 16000)
        self.assertEqual(t.channels, 1)
        self.assertEqual(t.sample_width, 2)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_feed_and_reset(self, _):
        from ovos_plugin_manager.templates.transformers import AudioTransformer
        t = AudioTransformer("audio-t")
        t.feed_audio_chunk(b"noise")
        t.feed_hotword_chunk(b"hotword")
        t.feed_speech_chunk(b"speech")
        self.assertGreater(len(t.noise_feed), 0)
        self.assertGreater(len(t.hotword_feed), 0)
        self.assertGreater(len(t.speech_feed), 0)

        t.reset()
        self.assertEqual(len(t.noise_feed), 0)
        self.assertEqual(len(t.hotword_feed), 0)
        self.assertEqual(len(t.speech_feed), 0)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_feed_speech_utterance(self, _):
        from ovos_plugin_manager.templates.transformers import AudioTransformer
        t = AudioTransformer("audio-t")
        audio = b"full-utterance"
        result = t.feed_speech_utterance(audio)
        self.assertEqual(result, audio)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_identity(self, _):
        from ovos_plugin_manager.templates.transformers import AudioTransformer
        t = AudioTransformer("audio-t")
        audio = b"raw-audio"
        out_audio, ctx = t.transform(audio)
        self.assertEqual(out_audio, audio)
        self.assertIsInstance(ctx, dict)


# ---------------------------------------------------------------------------
# DialogTransformer
# ---------------------------------------------------------------------------

class TestDialogTransformer(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_identity(self, _):
        from ovos_plugin_manager.templates.transformers import DialogTransformer
        t = DialogTransformer("dialog-t")
        dialog, ctx = t.transform("Hello there", context={"lang": "en-US"})
        self.assertEqual(dialog, "Hello there")
        self.assertEqual(ctx, {"lang": "en-US"})


# ---------------------------------------------------------------------------
# TTSTransformer
# ---------------------------------------------------------------------------

class TestTTSTransformer(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_identity(self, _):
        from ovos_plugin_manager.templates.transformers import TTSTransformer
        t = TTSTransformer("tts-t")
        wav, ctx = t.transform("/tmp/out.wav", context={})
        self.assertEqual(wav, "/tmp/out.wav")

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init_defaults(self, _):
        from ovos_plugin_manager.templates.transformers import TTSTransformer
        t = TTSTransformer("tts-t", priority=20)
        self.assertEqual(t.priority, 20)
        self.assertIsNone(t.bus)


# ---------------------------------------------------------------------------
# AudioLanguageDetector
# ---------------------------------------------------------------------------

class TestAudioLanguageDetector(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_injects_lang(self, _):
        t = _ConcreteAudioLangDetector("lang-detect")
        audio = b"audio-data"
        out_audio, ctx = t.transform(audio)
        self.assertEqual(out_audio, audio)
        self.assertEqual(ctx["stt_lang"], "en-US")
        self.assertAlmostEqual(ctx["lang_probability"], 0.99)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_detect(self, _):
        t = _ConcreteAudioLangDetector("lang-detect")
        lang, prob = t.detect(b"audio")
        self.assertEqual(lang, "en-US")
        self.assertEqual(prob, 0.99)


# ---------------------------------------------------------------------------
# find/load helpers
# ---------------------------------------------------------------------------

class TestTransformerPluginUtils(unittest.TestCase):
    PLUGIN_TYPE_MAP = {
        "utterance": (PluginTypes.UTTERANCE_TRANSFORMER,
                      PluginConfigTypes.UTTERANCE_TRANSFORMER),
        "metadata":  (PluginTypes.METADATA_TRANSFORMER,
                      PluginConfigTypes.METADATA_TRANSFORMER),
        "audio":     (PluginTypes.AUDIO_TRANSFORMER,
                      PluginConfigTypes.AUDIO_TRANSFORMER),
        "dialog":    (PluginTypes.DIALOG_TRANSFORMER,
                      PluginConfigTypes.DIALOG_TRANSFORMER),
        "tts":       (PluginTypes.TTS_TRANSFORMER,
                      PluginConfigTypes.TTS_TRANSFORMER),
        "intent":    (PluginTypes.INTENT_TRANSFORMER,
                      PluginConfigTypes.INTENT_TRANSFORMER),
    }

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_utterance_transformers(self, mock_find):
        from ovos_plugin_manager.text_transformers import find_utterance_transformer_plugins
        find_utterance_transformer_plugins()
        mock_find.assert_called_once_with(PluginTypes.UTTERANCE_TRANSFORMER)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_metadata_transformers(self, mock_find):
        from ovos_plugin_manager.metadata_transformers import find_metadata_transformer_plugins
        find_metadata_transformer_plugins()
        mock_find.assert_called_once_with(PluginTypes.METADATA_TRANSFORMER)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_audio_transformers(self, mock_find):
        from ovos_plugin_manager.audio_transformers import find_audio_transformer_plugins
        find_audio_transformer_plugins()
        mock_find.assert_called_once_with(PluginTypes.AUDIO_TRANSFORMER)

    @patch("ovos_plugin_manager.dialog_transformers.find_plugins")
    def test_find_dialog_transformers(self, mock_find):
        from ovos_plugin_manager.dialog_transformers import find_dialog_transformer_plugins
        find_dialog_transformer_plugins()
        mock_find.assert_called_once_with(PluginTypes.DIALOG_TRANSFORMER)
