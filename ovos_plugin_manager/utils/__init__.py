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
from enum import Enum
from threading import Event
from typing import Optional

import pkg_resources

from ovos_utils.log import LOG


class PluginTypes(str, Enum):
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


def normalize_lang(lang):
    # TODO consider moving to LF or ovos_utils
    # special handling, the parse sometimes messes this up
    # eg, uk-ua gets normalized to uk-gb
    # this also makes lookup easier as we
    # often get duplicate entries with both variants
    if "-" in lang:
        pieces = lang.split("-")
        if len(pieces) == 2 and pieces[0] == pieces[1]:
            lang = pieces[0]

    try:
        from langcodes import standardize_tag as _normalize_lang
        lang = _normalize_lang(lang, macro=True)
    except ValueError:
        # this lang code is apparently not valid ?
        pass
    return lang


class ReadWriteStream:
    """
    Class used to support writing binary audio data at any pace,
    optionally chopping when the buffer gets too large
    """

    def __init__(self, s=b'', chop_samples=-1):
        self.buffer = s
        self.write_event = Event()
        self.chop_samples = chop_samples

    def __len__(self):
        return len(self.buffer)

    def read(self, n=-1, timeout=None):
        if n == -1:
            n = len(self.buffer)
        if 0 < self.chop_samples < len(self.buffer):
            samples_left = len(self.buffer) % self.chop_samples
            self.buffer = self.buffer[-samples_left:]
        return_time = 1e10 if timeout is None else (
                timeout + time.time()
        )
        while len(self.buffer) < n:
            self.write_event.clear()
            if not self.write_event.wait(return_time - time.time()):
                return b''
        chunk = self.buffer[:n]
        self.buffer = self.buffer[n:]
        return chunk

    def write(self, s):
        self.buffer += s
        self.write_event.set()

    def flush(self):
        """Makes compatible with sys.stdout"""
        pass

    def clear(self):
        self.buffer = b''
