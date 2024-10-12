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
"""Common functions for loading plugins."""
import time
from collections import deque
from enum import Enum
from threading import Event, Lock
from typing import Optional

import pkg_resources
from ovos_utils.log import LOG, log_deprecation, deprecated


class PluginTypes(str, Enum):
    TRIPLES = "opm.triples"
    PIPELINE = "opm.pipeline"
    EMBEDDINGS = "opm.embeddings"
    FACE_EMBEDDINGS = "opm.embeddings.face"
    VOICE_EMBEDDINGS = "opm.embeddings.voice"
    TEXT_EMBEDDINGS = "opm.embeddings.text"
    GUI = "ovos.plugin.gui"
    PHAL = "ovos.plugin.phal"
    ADMIN = "ovos.plugin.phal.admin"
    SKILL = "ovos.plugin.skill"
    MIC = "ovos.plugin.microphone"
    VAD = "ovos.plugin.VAD"
    PHONEME = "ovos.plugin.g2p"
    AUDIO2IPA = "ovos.plugin.audio2ipa"
    AUDIO = 'mycroft.plugin.audioservice'  # DEPRECATED
    STT = 'mycroft.plugin.stt'
    TTS = 'mycroft.plugin.tts'
    WAKEWORD = 'mycroft.plugin.wake_word'
    TRANSLATE = "neon.plugin.lang.translate"
    LANG_DETECT = "neon.plugin.lang.detect"
    UTTERANCE_TRANSFORMER = "neon.plugin.text"
    METADATA_TRANSFORMER = "neon.plugin.metadata"
    AUDIO_TRANSFORMER = "neon.plugin.audio"
    DIALOG_TRANSFORMER = "opm.transformer.dialog"
    TTS_TRANSFORMER = "opm.transformer.tts"
    QUESTION_SOLVER = "neon.plugin.solver"
    TLDR_SOLVER = "opm.solver.summarization"
    ENTAILMENT_SOLVER = "opm.solver.entailment"
    MULTIPLE_CHOICE_SOLVER = "opm.solver.multiple_choice"
    READING_COMPREHENSION_SOLVER = "opm.solver.reading_comprehension"
    COREFERENCE_SOLVER = "intentbox.coreference"
    KEYWORD_EXTRACTION = "intentbox.keywords"
    UTTERANCE_SEGMENTATION = "intentbox.segmentation"
    TOKENIZATION = "intentbox.tokenization"
    POSTAG = "intentbox.postag"
    STREAM_EXTRACTOR = "ovos.ocp.extractor"
    AUDIO_PLAYER = "opm.media.audio"
    VIDEO_PLAYER = "opm.media.video"
    WEB_PLAYER = "opm.media.web"
    PERSONA = "opm.plugin.persona"  # personas are a dict, they have no config because they ARE a config


class PluginConfigTypes(str, Enum):
    TRIPLES = "opm.triples.config"
    PIPELINE = "opm.pipeline.config"
    EMBEDDINGS = "opm.embeddings.config"
    FACE_EMBEDDINGS = "opm.embeddings.face.config"
    VOICE_EMBEDDINGS = "opm.embeddings.voice.config"
    TEXT_EMBEDDINGS = "opm.embeddings.text.config"
    GUI = "ovos.plugin.gui.config"
    PHAL = "ovos.plugin.phal.config"
    ADMIN = "ovos.plugin.phal.admin.config"
    SKILL = "ovos.plugin.skill.config"
    VAD = "ovos.plugin.VAD.config"
    MIC = "ovos.plugin.microphone.config"
    PHONEME = "ovos.plugin.g2p.config"
    AUDIO2IPA = "ovos.plugin.audio2ipa.config"
    AUDIO = 'mycroft.plugin.audioservice.config'
    STT = 'mycroft.plugin.stt.config'
    TTS = 'mycroft.plugin.tts.config'
    WAKEWORD = 'mycroft.plugin.wake_word.config'
    TRANSLATE = "neon.plugin.lang.translate.config"
    LANG_DETECT = "neon.plugin.lang.detect.config"
    UTTERANCE_TRANSFORMER = "neon.plugin.text.config"
    METADATA_TRANSFORMER = "neon.plugin.metadata.config"
    AUDIO_TRANSFORMER = "neon.plugin.audio.config"
    DIALOG_TRANSFORMER = "opm.transformer.dialog.config"
    TTS_TRANSFORMER = "opm.transformer.tts.config"
    QUESTION_SOLVER = "neon.plugin.solver.config"
    TLDR_SOLVER = "opm.solver.summarization.config"
    ENTAILMENT_SOLVER = "opm.solver.entailment.config"
    MULTIPLE_CHOICE_SOLVER = "opm.solver.multiple_choice.config"
    READING_COMPREHENSION_SOLVER = "opm.solver.reading_comprehension.config"
    COREFERENCE_SOLVER = "intentbox.coreference.config"
    KEYWORD_EXTRACTION = "intentbox.keywords.config"
    UTTERANCE_SEGMENTATION = "intentbox.segmentation.config"
    TOKENIZATION = "intentbox.tokenization.config"
    POSTAG = "intentbox.postag.config"
    STREAM_EXTRACTOR = "ovos.ocp.extractor.config"
    AUDIO_PLAYER = "opm.media.audio.config"
    VIDEO_PLAYER = "opm.media.video.config"
    WEB_PLAYER = "opm.media.web.config"


def find_plugins(plug_type: PluginTypes = None) -> dict:
    """
    Finds all plugins matching specific entrypoint type.

    Arguments:
        plug_type (str): plugin entrypoint string to retrieve

    Returns:
        dict mapping plugin names to plugin entrypoints
    """
    entrypoints = {}
    if not plug_type:
        plugs = list(PluginTypes)
    elif isinstance(plug_type, str):
        plugs = [plug_type]
    else:
        plugs = plug_type
    for plug in plugs:
        for entry_point in _iter_entrypoints(plug):
            try:
                entrypoints[entry_point.name] = entry_point.load()
                if entry_point.name not in entrypoints:
                    LOG.debug(f"Loaded plugin entry point {entry_point.name}")
            except Exception as e:
                if entry_point not in find_plugins._errored:
                    find_plugins._errored.append(entry_point)
                    # NOTE: this runs in a loop inside skills manager, this would endlessly spam logs
                    LOG.error(f"Failed to load plugin entry point {entry_point}: "
                              f"{e}")
    return entrypoints


find_plugins._errored = []


def _iter_entrypoints(plug_type: Optional[str]):
    """
    Return an iterator containing all entrypoints of the requested type
    @param plug_type: entrypoint name to load
    @return: iterator of all entrypoints
    """
    try:
        from importlib_metadata import entry_points
        for entry_point in entry_points(group=plug_type):
            yield entry_point
    except ImportError:
        for entry_point in pkg_resources.iter_entry_points(plug_type):
            yield entry_point


def load_plugin(plug_name: str, plug_type: Optional[PluginTypes] = None):
    """Load a specific plugin from a specific plugin type.

    Arguments:
        plug_type: (str) plugin type name. Ex. "mycroft.plugin.tts".
        plug_name: (str) specific plugin name (else consider all plugin types)

    Returns:
        Loaded plugin Object or None if no matching object was found.
    """
    plugins = find_plugins(plug_type)
    if plug_name in plugins:
        return plugins[plug_name]
    plug_type = plug_type or "all plugin types"
    LOG.warning(f'Could not find the plugin {plug_type}.{plug_name}')
    return None

@deprecated("normalize_lang has been deprecated! update to 'from ovos_utils.lang import standardize_lang_tag'", "1.0.0")
def normalize_lang(lang):
    from ovos_utils.lang import standardize_lang_tag
    return standardize_lang_tag(lang)


class ReadWriteStream:
    """
    Class used to support writing binary audio data at any pace,
    with an optional maximum buffer size
    """

    def __init__(self, s=b'', chop_samples=-1, max_size=None):
        if chop_samples != -1:
            log_deprecation("'chop_samples' kwarg has been deprecated and will be ignored", "1.0.0")
        self.buffer = deque(s)
        self.write_event = Event()
        self.lock = Lock()
        self.max_size = max_size  # Introduce max size

    def __len__(self):
        with self.lock:
            return len(self.buffer)

    def read(self, n=-1, timeout=None):
        with self.lock:
            if n == -1 or n > len(self.buffer):
                n = len(self.buffer)

        end_time = time.time() + timeout if timeout is not None else float('inf')

        while True:
            with self.lock:
                if len(self.buffer) >= n:
                    chunk = bytes([self.buffer.popleft() for _ in range(n)])
                    return chunk

            remaining_time = None
            if timeout is not None:
                remaining_time = end_time - time.time()
                if remaining_time <= 0:
                    return b''

            self.write_event.clear()
            self.write_event.wait(remaining_time)

    def write(self, s):
        with self.lock:
            self.buffer.extend(s)
            if self.max_size is not None:
                while len(self.buffer) > self.max_size:
                    self.buffer.popleft()  # Discard oldest data to maintain max size
        self.write_event.set()

    def flush(self):
        """Makes compatible with sys.stdout"""
        pass

    def clear(self):
        with self.lock:
            self.buffer.clear()
