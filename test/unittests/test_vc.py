# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Unit tests for the voice-clone plugin family (opm.vc)."""
import unittest
from typing import Optional
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


# ---------------------------------------------------------------------------
# Concrete minimal implementation used across tests
# ---------------------------------------------------------------------------

class _ConcreteVC:
    """Minimal concrete implementation of VoiceClonePlugin for tests."""

    def __init__(self, config=None):
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin
        # Inherit dynamically so we can instantiate without import-time ABC machinery
        self.config = config or {}

    def clone_voice(self, audio: str, reference_voice: str,
                    out_path: Optional[str] = None) -> str:
        return out_path or "/tmp/cloned.wav"


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------

class TestVoiceClonePluginTemplate(unittest.TestCase):
    """Tests for ovos_plugin_manager.templates.vc.VoiceClonePlugin."""

    def test_import(self):
        """VoiceClonePlugin can be imported from the templates package."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin
        self.assertTrue(callable(VoiceClonePlugin))

    def test_is_abstract(self):
        """VoiceClonePlugin is abstract — direct instantiation raises TypeError."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin
        import abc
        # clone_voice must be abstract
        self.assertIn("clone_voice",
                      getattr(VoiceClonePlugin, "__abstractmethods__", set()))

    def test_exactly_one_abstract_method(self):
        """VoiceClonePlugin has exactly one abstract method: clone_voice."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin
        abstract_methods = getattr(VoiceClonePlugin, "__abstractmethods__", set())
        self.assertEqual(abstract_methods, {"clone_voice"},
                         "Contract violation: only clone_voice should be abstract")

    def test_concrete_subclass_instantiates(self):
        """A concrete subclass that implements clone_voice can be created."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Impl(VoiceClonePlugin):
            def clone_voice(self, audio, reference_voice, out_path=None):
                return out_path or "/tmp/out.wav"

        obj = _Impl(config={"key": "value"})
        self.assertEqual(obj.config, {"key": "value"})

    def test_clone_voice_returns_path(self):
        """clone_voice returns the expected output path."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Impl(VoiceClonePlugin):
            def clone_voice(self, audio, reference_voice, out_path=None):
                return out_path or "/tmp/out.wav"

        obj = _Impl()
        result = obj.clone_voice("/src.wav", "/ref.wav", "/out.wav")
        self.assertEqual(result, "/out.wav")

    def test_default_sample_rate(self):
        """sample_rate defaults to 24000."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Impl(VoiceClonePlugin):
            def clone_voice(self, audio, reference_voice, out_path=None):
                return "/tmp/out.wav"

        obj = _Impl()
        self.assertEqual(obj.sample_rate, 24000)

    def test_custom_sample_rate(self):
        """Subclasses can override sample_rate."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Impl(VoiceClonePlugin):
            sample_rate = 48000

            def clone_voice(self, audio, reference_voice, out_path=None):
                return "/tmp/out.wav"

        obj = _Impl()
        self.assertEqual(obj.sample_rate, 48000)

    def test_available_languages_default(self):
        """available_languages defaults to an empty list."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Impl(VoiceClonePlugin):
            def clone_voice(self, audio, reference_voice, out_path=None):
                return "/tmp/out.wav"

        obj = _Impl()
        self.assertEqual(obj.available_languages, [])

    def test_available_languages_custom(self):
        """Subclasses can override available_languages."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Impl(VoiceClonePlugin):
            available_languages = ["pt-PT", "en-US"]

            def clone_voice(self, audio, reference_voice, out_path=None):
                return "/tmp/out.wav"

        obj = _Impl()
        self.assertIn("pt-PT", obj.available_languages)

    def test_get_output_path_given(self):
        """_get_output_path returns the provided path when not None."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "sub", "out.wav")
            result = VoiceClonePlugin._get_output_path(target)
            self.assertEqual(result, target)
            self.assertTrue(os.path.isdir(os.path.dirname(result)))

    def test_get_output_path_none(self):
        """_get_output_path returns a valid temp path when None is passed."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin
        import os
        result = VoiceClonePlugin._get_output_path(None)
        self.assertTrue(result.endswith(".wav"))
        # Clean up the temp file
        if os.path.exists(result):
            os.unlink(result)

    def test_abc_enforcement_no_clone_voice(self):
        """Subclass missing clone_voice raises TypeError on instantiation."""
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _Broken(VoiceClonePlugin):
            pass  # clone_voice not implemented

        with self.assertRaises(TypeError):
            _Broken()


# ---------------------------------------------------------------------------
# PluginTypes / PluginConfigTypes enum tests
# ---------------------------------------------------------------------------

class TestVoiceClonePluginTypes(unittest.TestCase):
    """PluginTypes and PluginConfigTypes carry the correct opm.vc values."""

    def test_plugin_type_value(self):
        self.assertEqual(PluginTypes.VOICE_CLONE, "opm.vc")

    def test_plugin_config_type_value(self):
        self.assertEqual(PluginConfigTypes.VOICE_CLONE, "opm.vc.config")


# ---------------------------------------------------------------------------
# Discovery / loading module tests
# ---------------------------------------------------------------------------

class TestVoiceCloneModule(unittest.TestCase):
    """Tests for ovos_plugin_manager.vc discovery and loading wrappers."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_voice_clone_plugins(self, mock_find: MagicMock) -> None:
        """find_voice_clone_plugins calls find_plugins with VOICE_CLONE."""
        from ovos_plugin_manager.vc import find_voice_clone_plugins
        mock_find.return_value = {}
        find_voice_clone_plugins()
        mock_find.assert_called_once_with(PluginTypes.VOICE_CLONE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_voice_clone_plugin(self, mock_load: MagicMock) -> None:
        """load_voice_clone_plugin calls load_plugin with VOICE_CLONE."""
        from ovos_plugin_manager.vc import load_voice_clone_plugin
        mock_load.return_value = MagicMock()
        load_voice_clone_plugin("test-vc-plugin")
        mock_load.assert_called_once_with("test-vc-plugin", PluginTypes.VOICE_CLONE)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

_FACTORY_CONFIG = {
    "voice_clone": {
        "module": "dummy-vc",
        "dummy-vc": {
            "model_path": "/models/dummy.onnx",
        },
    }
}


class TestOVOSVoiceClonerFactory(unittest.TestCase):
    """Tests for OVOSVoiceClonerFactory."""

    def test_get_class(self):
        """get_class returns the class loaded by load_voice_clone_plugin."""
        from ovos_plugin_manager.vc import OVOSVoiceClonerFactory, load_voice_clone_plugin
        mock_cls = MagicMock()
        real_load = load_voice_clone_plugin.__module__

        with patch("ovos_plugin_manager.vc.load_voice_clone_plugin",
                   return_value=mock_cls) as mock_load:
            with patch("ovos_plugin_manager.vc.get_voice_clone_config",
                       return_value={"module": "dummy-vc"}):
                result = OVOSVoiceClonerFactory.get_class(_FACTORY_CONFIG)
        self.assertIs(result, mock_cls)

    def test_get_class_no_module_returns_none(self):
        """get_class returns None when no module is configured."""
        from ovos_plugin_manager.vc import OVOSVoiceClonerFactory
        with patch("ovos_plugin_manager.vc.get_voice_clone_config",
                   return_value={}):
            result = OVOSVoiceClonerFactory.get_class({})
        self.assertIsNone(result)

    def test_create_instantiates_plugin(self):
        """create() returns an instance of the plugin class."""
        from ovos_plugin_manager.vc import OVOSVoiceClonerFactory
        from ovos_plugin_manager.templates.vc import VoiceClonePlugin

        class _DummyVC(VoiceClonePlugin):
            def clone_voice(self, audio, reference_voice, out_path=None):
                return out_path or "/tmp/out.wav"

        with patch("ovos_plugin_manager.vc.get_voice_clone_config",
                   return_value={"module": "dummy-vc", "dummy-vc": {"x": 1}}):
            with patch("ovos_plugin_manager.vc.OVOSVoiceClonerFactory.get_class",
                       return_value=_DummyVC):
                instance = OVOSVoiceClonerFactory.create(_FACTORY_CONFIG)
        self.assertIsInstance(instance, _DummyVC)
        self.assertEqual(instance.config, {"x": 1})

    def test_create_raises_when_class_none(self):
        """create() raises RuntimeError when the plugin class cannot be found."""
        from ovos_plugin_manager.vc import OVOSVoiceClonerFactory
        with patch("ovos_plugin_manager.vc.get_voice_clone_config",
                   return_value={"module": "missing-plugin"}):
            with patch("ovos_plugin_manager.vc.OVOSVoiceClonerFactory.get_class",
                       return_value=None):
                with self.assertRaises(RuntimeError):
                    OVOSVoiceClonerFactory.create({})

    def test_create_propagates_exception(self):
        """create() re-raises when plugin construction fails."""
        from ovos_plugin_manager.vc import OVOSVoiceClonerFactory

        def _exploding(*a, **kw):
            raise ValueError("bad config")

        with patch("ovos_plugin_manager.vc.get_voice_clone_config",
                   return_value={"module": "dummy-vc", "dummy-vc": {}}):
            with patch("ovos_plugin_manager.vc.OVOSVoiceClonerFactory.get_class",
                       return_value=_exploding):
                with self.assertRaises(ValueError):
                    OVOSVoiceClonerFactory.create({})


if __name__ == "__main__":
    unittest.main()
