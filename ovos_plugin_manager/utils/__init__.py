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
from collections import deque

import pkg_resources
import time
import warnings
from enum import Enum
from ovos_utils.log import LOG, log_deprecation, deprecated
from threading import Event, Lock
from typing import Optional, Union

DEPRECATED_ENTRYPOINTS = {
    "ovos.plugin.gui": "opm.gui",
    "ovos.plugin.phal": "opm.phal",
    "ovos.plugin.phal.admin": "opm.phal.admin",
    "ovos.plugin.skill": "opm.skill",
    "ovos.plugin.microphone": "opm.microphone",
    "ovos.plugin.VAD": "opm.vad",
    "ovos.plugin.g2p": "opm.g2p",
    "ovos.plugin.audio2ipa": "opm.audio2ipa",
    'mycroft.plugin.stt': "opm.stt",
    'mycroft.plugin.tts': "opm.tts",
    'mycroft.plugin.wake_word': "opm.wake_word",
    "neon.plugin.lang.translate": "opm.lang.translate",
    "neon.plugin.lang.detect": "opm.lang.detect",
    "neon.plugin.text": "opm.transformer.text",
    "neon.plugin.metadata": "opm.transformer.metadata",
    "neon.plugin.audio": "opm.transformer.audio",
    "neon.plugin.solver": "opm.solver.question",
    "intentbox.coreference": "opm.coreference",
    "intentbox.keywords": "opm.keywords",
    "intentbox.segmentation": "opm.segmentation",
    "intentbox.tokenization": "opm.tokenization",
    "intentbox.postag": "opm.postag",
    "ovos.ocp.extractor": "opm.ocp.extractor"
}


class PluginTypes(str, Enum):
    TRIPLES = "opm.triples"
    PIPELINE = "opm.pipeline"
    EMBEDDINGS = "opm.embeddings"
    IMAGE_EMBEDDINGS = "opm.embeddings.image"
    FACE_EMBEDDINGS = "opm.embeddings.face"
    VOICE_EMBEDDINGS = "opm.embeddings.voice"
    TEXT_EMBEDDINGS = "opm.embeddings.text"
    GUI = "opm.gui"
    PHAL = "opm.phal"
    ADMIN = "opm.phal.admin"
    SKILL = "opm.skill"
    MIC = "opm.microphone"
    VAD = "opm.VAD"
    PHONEME = "opm.g2p"
    AUDIO2IPA = "opm.audio2ipa"
    AUDIO = 'mycroft.plugin.audioservice'  # DEPRECATED
    STT = 'opm.stt'
    TTS = 'opm.tts'
    WAKEWORD = 'opm.wake_word'
    TRANSLATE = "opm.lang.translate"
    LANG_DETECT = "opm.lang.detect"
    UTTERANCE_TRANSFORMER = "opm.transformer.text"
    METADATA_TRANSFORMER = "opm.transformer.metadata"
    AUDIO_TRANSFORMER = "opm.transformer.audio"
    DIALOG_TRANSFORMER = "opm.transformer.dialog"
    TTS_TRANSFORMER = "opm.transformer.tts"
    INTENT_TRANSFORMER = "opm.transformer.intent"
    QUESTION_SOLVER = "opm.solver.question"
    CHAT_SOLVER = "opm.solver.chat"
    TLDR_SOLVER = "opm.solver.summarization"
    ENTAILMENT_SOLVER = "opm.solver.entailment"
    MULTIPLE_CHOICE_SOLVER = "opm.solver.multiple_choice"
    READING_COMPREHENSION_SOLVER = "opm.solver.reading_comprehension"
    COREFERENCE_SOLVER = "opm.coreference"
    KEYWORD_EXTRACTION = "opm.keywords"
    UTTERANCE_SEGMENTATION = "opm.segmentation"
    TOKENIZATION = "opm.tokenization"
    POSTAG = "opm.postag"
    STREAM_EXTRACTOR = "opm.ocp.extractor"
    AUDIO_PLAYER = "opm.media.audio"
    VIDEO_PLAYER = "opm.media.video"
    WEB_PLAYER = "opm.media.web"
    PERSONA = "opm.plugin.persona"  # personas are a dict, they have no config because they ARE a config


class PluginConfigTypes(str, Enum):
    TRIPLES = "opm.triples.config"
    PIPELINE = "opm.pipeline.config"
    EMBEDDINGS = "opm.embeddings.config"
    IMAGE_EMBEDDINGS = "opm.embeddings.image.config"
    FACE_EMBEDDINGS = "opm.embeddings.face.config"
    VOICE_EMBEDDINGS = "opm.embeddings.voice.config"
    TEXT_EMBEDDINGS = "opm.embeddings.text.config"
    GUI = "opm.gui.config"
    PHAL = "opm.phal.config"
    ADMIN = "opm.phal.admin.config"
    SKILL = "opm.skill.config"
    VAD = "opm.VAD.config"
    MIC = "opm.microphone.config"
    PHONEME = "opm.g2p.config"
    AUDIO2IPA = "opm.audio2ipa.config"
    AUDIO = 'mycroft.plugin.audioservice.config'  # DEPRECATED
    STT = 'opm.stt.config'
    TTS = 'opm.tts.config'
    WAKEWORD = 'opm.wake_word.config'
    TRANSLATE = "opm.lang.translate.config"
    LANG_DETECT = "opm.lang.detect.config"
    UTTERANCE_TRANSFORMER = "opm.transformer.text.config"
    METADATA_TRANSFORMER = "opm.transformer.metadata.config"
    AUDIO_TRANSFORMER = "opm.transformer.audio.config"
    DIALOG_TRANSFORMER = "opm.transformer.dialog.config"
    TTS_TRANSFORMER = "opm.transformer.tts.config"
    INTENT_TRANSFORMER = "opm.transformer.intent.config"
    QUESTION_SOLVER = "opm.solver.config"
    CHAT_SOLVER = "opm.solver.chat.config"
    TLDR_SOLVER = "opm.solver.summarization.config"
    ENTAILMENT_SOLVER = "opm.solver.entailment.config"
    MULTIPLE_CHOICE_SOLVER = "opm.solver.multiple_choice.config"
    READING_COMPREHENSION_SOLVER = "opm.solver.reading_comprehension.config"
    COREFERENCE_SOLVER = "opm.coreference.config"
    KEYWORD_EXTRACTION = "opm.keywords.config"
    UTTERANCE_SEGMENTATION = "opm.segmentation.config"
    TOKENIZATION = "opm.tokenization.config"
    POSTAG = "opm.postag.config"
    STREAM_EXTRACTOR = "opm.ocp.extractor.config"
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

# compat with older python versions
try:
    from importlib_metadata import entry_points


    def _iter_plugins(plug_type):
        """
        Yields all entry points for the specified plugin group.
        
        Parameters:
            plug_type: The entry point group name to search for.
        
        Yields:
            Entry points belonging to the specified group.
        """
        for entry_point in entry_points(group=plug_type):
            yield entry_point
except ImportError:
    def _iter_plugins(plug_type):
        """
        Yield all entry points for the specified plugin group using pkg_resources.
        
        Parameters:
            plug_type (str): The entry point group name to search for.
        
        Yields:
            EntryPoint: Each discovered entry point in the specified group.
        """
        for entry_point in pkg_resources.iter_entry_points(plug_type):
            yield entry_point


def _iter_entrypoints(plug_type: Union[str, PluginTypes]):
    """
    Yield all entry points for the specified plugin type, including deprecated identifiers for backward compatibility.
    
    Parameters:
        plug_type (str or PluginTypes): The entry point group name or PluginTypes enum value to search for.
    
    Yields:
        Entry points matching the requested type, including those found under deprecated group names with a warning.
    """
    OLD = {v: k for k, v in DEPRECATED_ENTRYPOINTS.items()}
    identifier = plug_type.value if isinstance(plug_type, PluginTypes) else plug_type
    old_identifier = OLD.get(plug_type)

    if identifier in DEPRECATED_ENTRYPOINTS:
        LOG.warning(
            f"requested old style identifier, please update your code to request '{old_identifier}' instead of '{identifier}'")
        identifier, old_identifier = DEPRECATED_ENTRYPOINTS[identifier], identifier

    for entry_point in _iter_plugins(identifier):
        yield entry_point

    if old_identifier:
        for e in _iter_plugins(old_identifier):
            if e.name not in _iter_entrypoints._warnings:
                _iter_entrypoints._warnings.append(e.name)
                LOG.warning(
                    f"old style entrypoint detected for plugin '{e.name}' - '{old_identifier}' should be renamed to '{identifier}'")
            yield e


_iter_entrypoints._warnings = []


def load_plugin(plug_name: str, plug_type: Optional[PluginTypes] = None):
    """
    Load a plugin by name from the specified plugin type.
    
    If the plugin is found, returns the loaded plugin object; otherwise, returns None and logs a warning.
    
    Parameters:
        plug_name (str): The name of the plugin to load.
        plug_type (Optional[PluginTypes]): The plugin type to search within. If not provided, searches all plugin types.
    
    Returns:
        The loaded plugin object if found; otherwise, None.
    """
    plugins = find_plugins(plug_type)
    if plug_name in plugins:
        return plugins[plug_name]
    plug_type = plug_type or "all plugin types"
    LOG.warning(f'Could not find the plugin {plug_type}.{plug_name}')
    return None


@deprecated("normalize_lang has been deprecated! update to 'from ovos_utils.lang import standardize_lang_tag'", "1.0.0")
def normalize_lang(lang):
    warnings.warn(
        "update to 'from ovos_utils.lang import standardize_lang_tag'",
        DeprecationWarning,
        stacklevel=2,
    )
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
