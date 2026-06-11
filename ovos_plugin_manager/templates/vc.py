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
"""Abstract base class for voice-cloning (audio → audio) plugins."""
import abc
import os
import tempfile
from typing import Dict, List, Optional


class VoiceClonePlugin(abc.ABC):
    """Base class for voice-cloning plugins.

    A voice-cloning plugin converts source speech audio to sound like a
    reference speaker while preserving the linguistic content of the source.
    This is a pure audio-to-audio contract: the plugin receives two audio
    files and returns a new audio file.

    Plugin authors must implement :meth:`clone_voice`.

    Entry-point group: ``opm.vc``
    Config section: ``voice_clone``

    Example pyproject.toml registration::

        [project.entry-points."opm.vc"]
        my-vc-plugin = "my_package.vc:MyVoiceClonePlugin"

    Attributes:
        config: Plugin configuration dictionary passed at construction time.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialise the plugin with an optional configuration dictionary.

        Args:
            config: Plugin-specific configuration. Plugins may document their
                supported keys in settingsmeta.json.
        """
        self.config: Dict = config or {}

    # ------------------------------------------------------------------
    # Required contract
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def clone_voice(
        self,
        audio: str,
        reference_voice: str,
        out_path: Optional[str] = None,
    ) -> str:
        """Convert source speech to sound like *reference_voice*.

        Args:
            audio: Path to the source speech WAV file whose linguistic
                content should be preserved.
            reference_voice: Path to a short reference WAV file that
                provides the target voice timbre/style.
            out_path: Desired output file path.  If ``None`` the
                implementation should write to a temporary file and
                return its path.

        Returns:
            Absolute path to the output 16-bit WAV file.  The sample rate
            is documented by the plugin via :attr:`sample_rate`.

        Raises:
            NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Optional properties / helpers
    # ------------------------------------------------------------------

    @property
    def sample_rate(self) -> int:
        """Output sample rate in Hz.

        Plugins should override this to advertise the sample rate of the
        WAV files they produce.  Defaults to 24000 Hz.
        """
        return 24000

    @property
    def available_languages(self) -> List[str]:
        """BCP-47 language tags supported by this plugin.

        Return an empty list (the default) for language-agnostic plugins
        that operate on raw acoustic features regardless of language.
        """
        return []

    # ------------------------------------------------------------------
    # Convenience helper
    # ------------------------------------------------------------------

    @staticmethod
    def _get_output_path(out_path: Optional[str], suffix: str = ".wav") -> str:
        """Return *out_path* if set, otherwise a fresh temporary file path.

        Args:
            out_path: Caller-supplied path or ``None``.
            suffix: File extension for the temporary file.

        Returns:
            A writable file path.
        """
        if out_path:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            return out_path
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        return path
