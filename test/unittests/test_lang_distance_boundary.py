"""The language-distance boundary used to select dialect plugin configs."""
import importlib.util
import unittest

from ovos_plugin_manager.utils.config import get_valid_plugin_configs

# linguatag (Python >= 3.11) separates the Sinitic languages from Mandarin;
# the langcodes matcher that Python 3.10 resolves does not.
LINGUATAG = importlib.util.find_spec("linguatag") is not None

MACROLANGUAGE_PAIRS = [("arz", "ar")] + ([("cmn", "zh")] if LINGUATAG else [])
REGIONAL_PAIRS = [("ar-SA", "ar"), ("en-AU", "en-GB"), ("pt-BR", "pt-PT")]
UNRELATED_PAIRS = [("en", "zh"), ("es", "fr"), ("fr-CH", "de-CH"), ("af", "nl")] + \
                  ([("wuu", "zh")] if LINGUATAG else [])


def _selected(requested: str, available: str) -> bool:
    """True when the config filed under `available` is offered for `requested`."""
    configs = {available: [{"module": "test", "priority": 50}]}
    return bool(get_valid_plugin_configs(configs, requested,
                                         include_dialects=True))


class TestValidPluginConfigLangBoundary(unittest.TestCase):

    def test_macrolanguage_config_is_offered(self):
        for member, macro in MACROLANGUAGE_PAIRS:
            with self.subTest(member=member):
                self.assertTrue(_selected(member, macro))

    def test_regional_config_is_offered(self):
        for requested, available in REGIONAL_PAIRS:
            with self.subTest(requested=requested):
                self.assertTrue(_selected(requested, available))

    def test_unrelated_config_is_not_offered(self):
        for requested, available in UNRELATED_PAIRS:
            with self.subTest(requested=requested):
                self.assertFalse(_selected(requested, available))


if __name__ == "__main__":
    unittest.main()
