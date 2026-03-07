import unittest
from unittest.mock import patch, MagicMock, Mock

from ovos_plugin_manager.utils import PluginTypes


class TestOpenVoiceOSPlugin(unittest.TestCase):

    def _make_plugin(self, data=None):
        """
        Create an OpenVoiceOSPlugin test instance using the provided raw plugin data.
        
        Parameters:
            data (dict | None): Raw plugin metadata to initialize the plugin with; if None, an empty dict is used.
        
        Returns:
            OpenVoiceOSPlugin: A new plugin instance initialized from `data` (or an empty dict).
        """
        from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin
        return OpenVoiceOSPlugin(data or {})

    # ------------------------------------------------------------------ #
    # Construction & properties from raw data                             #
    # ------------------------------------------------------------------ #

    def test_name(self):
        p = self._make_plugin({"name": "ovos-stt-plugin-whisper"})
        self.assertEqual(p.name, "ovos-stt-plugin-whisper")

    def test_name_missing(self):
        p = self._make_plugin({})
        self.assertIsNone(p.name)

    def test_package_name(self):
        p = self._make_plugin({"package_name": "ovos-stt-plugin-whisper"})
        self.assertEqual(p.package_name, "ovos-stt-plugin-whisper")

    def test_url(self):
        url = "https://github.com/OpenVoiceOS/ovos-stt-plugin-whisper"
        p = self._make_plugin({"url": url})
        self.assertEqual(p.url, url)

    def test_description_from_data(self):
        p = self._make_plugin({"description": "A great plugin"})
        self.assertEqual(p.description, "A great plugin")

    def test_json_keys(self):
        p = self._make_plugin({"name": "test-plugin"})
        j = p.json
        for key in ("name", "package_name", "module_name", "human_name",
                    "description", "plugin_type", "url", "is_installed",
                    "class"):
            self.assertIn(key, j)

    # ------------------------------------------------------------------ #
    # human_name derivation                                               #
    # ------------------------------------------------------------------ #

    def test_human_name_from_data(self):
        p = self._make_plugin({"human_name": "My Great Plugin"})
        self.assertEqual(p.human_name, "My Great Plugin")

    def test_human_name_from_package_name(self):
        """
        Ensure human_name is derived from package_name when the plugin class is not installed.
        
        Patches the plugin's `clazz` to None to simulate an uninstalled plugin and asserts that `human_name` is produced (not None), falling back to `package_name` or `name`.
        """
        p = self._make_plugin({"package_name": "ovos-tts-plugin-piper"})
        # clazz is None (not installed), falls back to package_name
        with patch.object(type(p), "clazz", new_callable=lambda: property(lambda _: None)):
            name = p.human_name
        # human_name should be derived from package_name or name
        self.assertIsNotNone(name)

    # ------------------------------------------------------------------ #
    # plugin_type heuristics                                              #
    # ------------------------------------------------------------------ #

    def test_plugin_type_explicit(self):
        p = self._make_plugin({"plugin_type": PluginTypes.TTS})
        self.assertEqual(p.plugin_type, PluginTypes.TTS)

    def test_plugin_type_from_name_tts(self):
        p = self._make_plugin({"name": "my-custom-tts-plugin"})
        # not installed, heuristic from name
        with patch("ovos_plugin_manager.plugin_entry.find_stt_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_tts_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_wake_word_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_audio_service_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.load_plugin", return_value=None):
            pt = p.plugin_type
        self.assertEqual(pt, PluginTypes.TTS)

    def test_plugin_type_from_name_stt(self):
        p = self._make_plugin({"name": "my-custom-stt-engine"})
        with patch("ovos_plugin_manager.plugin_entry.find_stt_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_tts_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_wake_word_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_audio_service_plugins", return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.load_plugin", return_value=None):
            pt = p.plugin_type
        self.assertEqual(pt, PluginTypes.STT)

    # ------------------------------------------------------------------ #
    # is_installed / clazz / load                                        #
    # ------------------------------------------------------------------ #

    def test_not_installed_when_load_returns_none(self):
        p = self._make_plugin({"name": "nonexistent-plugin"})
        with patch("ovos_plugin_manager.plugin_entry.load_plugin", return_value=None):
            self.assertFalse(p.is_installed)
            self.assertIsNone(p.clazz)

    def test_is_installed_when_load_returns_class(self):
        fake_class = type("FakeTTS", (), {"__module__": "fake_module",
                                          "__doc__": "Fake TTS"})
        p = self._make_plugin({"name": "some-plugin"})
        with patch("ovos_plugin_manager.plugin_entry.load_plugin",
                   return_value=fake_class):
            self.assertTrue(p.is_installed)
            self.assertIs(p.clazz, fake_class)

    def test_module_name_from_installed_class(self):
        fake_class = type("FakeTTS", (), {"__module__": "my_tts_module"})
        p = self._make_plugin({"name": "some-plugin"})
        with patch("ovos_plugin_manager.plugin_entry.load_plugin",
                   return_value=fake_class):
            self.assertEqual(p.module_name, "my_tts_module")

    def test_description_falls_back_to_class_docstring(self):
        fake_class = type("FakeTTS", (), {"__module__": "m",
                                          "__doc__": "Docstring description"})
        p = self._make_plugin({"name": "some-plugin"})
        with patch("ovos_plugin_manager.plugin_entry.load_plugin",
                   return_value=fake_class):
            self.assertEqual(p.description, "Docstring description")

    # ------------------------------------------------------------------ #
    # install                                                             #
    # ------------------------------------------------------------------ #

    def test_install_via_package_name(self):
        p = self._make_plugin({"package_name": "ovos-stt-plugin-whisper"})
        with patch("ovos_plugin_manager.plugin_entry.pip_install",
                   return_value=True) as mock_pip:
            result = p.install()
        mock_pip.assert_called_once_with("ovos-stt-plugin-whisper")
        self.assertTrue(result)

    def test_install_via_github_url(self):
        url = "https://github.com/OpenVoiceOS/ovos-stt-plugin-whisper"
        p = self._make_plugin({"url": url})
        with patch("ovos_plugin_manager.plugin_entry.pip_install",
                   return_value=True) as mock_pip:
            result = p.install()
        mock_pip.assert_called_once_with("git+" + url)
        self.assertTrue(result)

    def test_install_returns_false_without_source(self):
        """
        Verifies that install() fails when the plugin has no install source and cannot be loaded.
        
        Asserts that install() returns False for a plugin with only a name and no package or URL when the plugin loader reports the plugin is not available.
        """
        p = self._make_plugin({"name": "some-plugin"})
        with patch("ovos_plugin_manager.plugin_entry.load_plugin", return_value=None):
            result = p.install()
        self.assertFalse(result)

    # ------------------------------------------------------------------ #
    # from_name factory                                                   #
    # ------------------------------------------------------------------ #

    def test_from_name_returns_instance(self):
        from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin
        with patch("ovos_plugin_manager.plugin_entry.find_stt_plugins",
                   return_value={"my-stt": object()}), \
             patch("ovos_plugin_manager.plugin_entry.find_tts_plugins",
                   return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_wake_word_plugins",
                   return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.find_audio_service_plugins",
                   return_value={}), \
             patch("ovos_plugin_manager.plugin_entry.load_plugin",
                   return_value=None):
            p = OpenVoiceOSPlugin.from_name("my-stt")
        self.assertIsInstance(p, OpenVoiceOSPlugin)
        self.assertEqual(p.name, "my-stt")
