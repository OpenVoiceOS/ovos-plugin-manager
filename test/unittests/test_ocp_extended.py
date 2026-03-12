# Copyright 2024, OpenVoiceOS
#
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

"""Extended unit tests for ovos_plugin_manager.ocp (StreamHandler and helpers)."""

import unittest
from unittest.mock import MagicMock, patch, call

from ovos_plugin_manager.utils import PluginTypes


class TestFindOCPFunctions(unittest.TestCase):
    """Tests for the simple find_* functions in ocp.py."""

    @patch("ovos_plugin_manager.ocp.find_plugins")
    def test_find_ocp_plugins(self, mock_find: MagicMock) -> None:
        """find_ocp_plugins calls find_plugins with STREAM_EXTRACTOR."""
        from ovos_plugin_manager.ocp import find_ocp_plugins
        mock_find.return_value = {}
        find_ocp_plugins()
        mock_find.assert_called_once_with(PluginTypes.STREAM_EXTRACTOR)

    @patch("ovos_plugin_manager.ocp.find_plugins")
    def test_find_ocp_audio_plugins(self, mock_find: MagicMock) -> None:
        """find_ocp_audio_plugins calls find_plugins with AUDIO_PLAYER."""
        from ovos_plugin_manager.ocp import find_ocp_audio_plugins
        mock_find.return_value = {}
        find_ocp_audio_plugins()
        mock_find.assert_called_once_with(PluginTypes.AUDIO_PLAYER)

    @patch("ovos_plugin_manager.ocp.find_plugins")
    def test_find_ocp_video_plugins(self, mock_find: MagicMock) -> None:
        """find_ocp_video_plugins calls find_plugins with VIDEO_PLAYER."""
        from ovos_plugin_manager.ocp import find_ocp_video_plugins
        mock_find.return_value = {}
        find_ocp_video_plugins()
        mock_find.assert_called_once_with(PluginTypes.VIDEO_PLAYER)

    @patch("ovos_plugin_manager.ocp.find_plugins")
    def test_find_ocp_web_plugins(self, mock_find: MagicMock) -> None:
        """find_ocp_web_plugins calls find_plugins with WEB_PLAYER."""
        from ovos_plugin_manager.ocp import find_ocp_web_plugins
        mock_find.return_value = {}
        find_ocp_web_plugins()
        mock_find.assert_called_once_with(PluginTypes.WEB_PLAYER)


class TestStreamHandler(unittest.TestCase):
    """Tests for StreamHandler class."""

    @patch("ovos_plugin_manager.ocp.find_ocp_plugins")
    def test_load_plugins(self, mock_find: MagicMock) -> None:
        """StreamHandler.load() instantiates discovered plugins."""
        from ovos_plugin_manager.ocp import StreamHandler
        mock_cls = MagicMock()
        mock_find.return_value = {"test-plug": mock_cls}
        handler = StreamHandler()
        self.assertIn("test-plug", handler.extractors)
        mock_cls.assert_called_once()

    @patch("ovos_plugin_manager.ocp.find_ocp_plugins")
    def test_load_plugins_failure_skipped(self, mock_find: MagicMock) -> None:
        """StreamHandler.load() skips plugins that fail to instantiate."""
        from ovos_plugin_manager.ocp import StreamHandler
        bad_cls = MagicMock(side_effect=RuntimeError("fail"))
        mock_find.return_value = {"bad": bad_cls}
        handler = StreamHandler()
        self.assertNotIn("bad", handler.extractors)

    @patch("ovos_plugin_manager.ocp.find_ocp_plugins")
    def test_supported_seis(self, mock_find: MagicMock) -> None:
        """supported_seis aggregates seis from all extractors."""
        from ovos_plugin_manager.ocp import StreamHandler
        mock_extractor = MagicMock()
        mock_extractor.supported_seis = ["yt", "spotify"]
        mock_cls = MagicMock(return_value=mock_extractor)
        mock_find.return_value = {"plug": mock_cls}
        handler = StreamHandler()
        self.assertIn("yt", handler.supported_seis)
        self.assertIn("spotify", handler.supported_seis)

    @patch("ovos_plugin_manager.ocp.find_ocp_plugins")
    def test_extract_stream_no_extractors(self, mock_find: MagicMock) -> None:
        """extract_stream returns {'uri': uri} when no extractors match."""
        from ovos_plugin_manager.ocp import StreamHandler
        mock_find.return_value = {}
        handler = StreamHandler()
        result = handler.extract_stream("http://example.com/audio.mp3")
        self.assertEqual(result, {"uri": "http://example.com/audio.mp3"})

    @patch("ovos_plugin_manager.ocp.find_ocp_plugins")
    def test_extract_stream_with_sei_extractor(self, mock_find: MagicMock) -> None:
        """extract_stream uses SEI extractor when uri matches."""
        from ovos_plugin_manager.ocp import StreamHandler
        mock_extractor = MagicMock()
        mock_extractor.supported_seis = ["yt"]
        mock_extractor.extract_stream.return_value = {"uri": "https://real-stream.com/v.mp4"}
        mock_extractor.validate_uri.return_value = False
        mock_cls = MagicMock(return_value=mock_extractor)
        mock_find.return_value = {"yt-plug": mock_cls}
        handler = StreamHandler()
        result = handler.extract_stream("yt//https://youtube.com/watch?v=123")
        self.assertIn("uri", result)

    @patch("ovos_plugin_manager.ocp.find_ocp_plugins")
    def test_extract_stream_url_extractor(self, mock_find: MagicMock) -> None:
        """extract_stream falls back to URL-matching extractor."""
        from ovos_plugin_manager.ocp import StreamHandler
        mock_extractor = MagicMock()
        mock_extractor.supported_seis = []
        mock_extractor.validate_uri.return_value = True
        mock_extractor.extract_stream.return_value = {"uri": "https://stream.com/audio.m3u8"}
        mock_cls = MagicMock(return_value=mock_extractor)
        mock_find.return_value = {"url-plug": mock_cls}
        handler = StreamHandler()
        result = handler.extract_stream("https://example.com/video")
        self.assertIn("uri", result)


class TestAvailableExtractors(unittest.TestCase):
    """Tests for available_extractors function."""

    @patch("ovos_plugin_manager.ocp.load_stream_extractors")
    def test_available_extractors_base(self, mock_load: MagicMock) -> None:
        """available_extractors always includes http/https/file."""
        from ovos_plugin_manager.ocp import available_extractors
        mock_handler = MagicMock()
        mock_handler.supported_seis = []
        mock_load.return_value = mock_handler
        result = available_extractors()
        self.assertIn("http:", result)
        self.assertIn("https:", result)
        self.assertIn("file:", result)

    @patch("ovos_plugin_manager.ocp.load_stream_extractors")
    def test_available_extractors_with_sei(self, mock_load: MagicMock) -> None:
        """available_extractors includes sei// entries."""
        from ovos_plugin_manager.ocp import available_extractors
        mock_handler = MagicMock()
        mock_handler.supported_seis = ["yt", "sc"]
        mock_load.return_value = mock_handler
        result = available_extractors()
        self.assertIn("yt//", result)
        self.assertIn("sc//", result)


if __name__ == "__main__":
    unittest.main()
