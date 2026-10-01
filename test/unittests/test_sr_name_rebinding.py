# Copyright 2026, OpenVoiceOS
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

"""What importing ovos_plugin_manager.utils.audio does to speech_recognition.

Importing this package rebinds speech_recognition.AudioData, so a plugin that
asserts isinstance against it keeps working. It must NOT rebind
speech_recognition.AudioFile: our class subclasses the vendored srAudioFile
and not the installed speech_recognition.AudioSource, and
Recognizer.record() asserts isinstance(source, AudioSource) on its first
line.
"""

import struct
import unittest
import wave
from io import BytesIO

import speech_recognition as sr

# the import under test: it runs the rebinding at module level
from ovos_plugin_manager.utils.audio import AudioData


def _wav_bytes(num_samples: int = 1600, sample_rate: int = 16000) -> BytesIO:
    buf = BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(struct.pack(f"<{num_samples}h",
                                       *([0] * num_samples)))
    buf.seek(0)
    return buf


class TestSpeechRecognitionNameRebinding(unittest.TestCase):

    def test_audiodata_is_rebound(self):
        """The half the patch exists for. One live consumer asserts on it."""
        self.assertIs(sr.AudioData, AudioData)

    def test_audiofile_is_not_rebound(self):
        """The half that broke its own consumers."""
        self.assertTrue(issubclass(sr.AudioFile, sr.AudioSource),
                        "speech_recognition.AudioFile must stay an "
                        "AudioSource; Recognizer.record() asserts on it")

    def test_record_accepts_an_audiofile(self):
        """The shape ovos-stt-plugin-pocketsphinx and the plugin-author page
        in OpenVoiceOS/Agent-Skills both use."""
        recognizer = sr.Recognizer()
        with sr.AudioFile(_wav_bytes()) as source:
            audio = recognizer.record(source)
        self.assertIsInstance(audio, sr.AudioData)

    def test_our_audiodata_satisfies_the_consumer_assertion(self):
        """ovos-stt-plugin-deepgram asserts isinstance(x, sr.AudioData)."""
        ours = AudioData(struct.pack("<100h", *([0] * 100)), 16000, 2)
        self.assertIsInstance(ours, sr.AudioData)


if __name__ == "__main__":
    unittest.main()
