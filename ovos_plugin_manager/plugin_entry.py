from typing import Optional, Type

from ovos_plugin_manager.tts import find_tts_plugins
from ovos_plugin_manager.stt import find_stt_plugins
from ovos_plugin_manager.wakewords import find_wake_word_plugins
from ovos_plugin_manager.audio import find_audio_service_plugins
from ovos_plugin_manager.utils import load_plugin, PluginTypes
from ovos_plugin_manager.installation import pip_install
from ovos_utils import camel_case_split
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import log_deprecation
from ovos_plugin_manager.version import VERSION_MAJOR

# Calculate next major version for deprecation
_deprecation_version = f"{VERSION_MAJOR + 1}.0"

# Deprecation notice for this module
log_deprecation(f"ovos_plugin_manager.plugin_entry module is deprecated and will be removed in v{_deprecation_version}",
                func_name="plugin_entry module",
                func_module="ovos_plugin_manager.plugin_entry",
                deprecation_version=_deprecation_version)


class OpenVoiceOSPlugin:
    """Metadata wrapper for an OVOS plugin — installed or not.

    Can be constructed from raw metadata dict or looked up by entry point name
    via :meth:`from_name`. Provides lazy loading: the plugin class is only
    imported the first time :attr:`clazz` is accessed.
    """

    def __init__(self, data: dict):
        """
        Create an OpenVoiceOSPlugin metadata wrapper from a raw metadata dictionary.
        
        Parameters:
            data (dict): Metadata dictionary for the plugin. Recognized keys:
                - name: entry point name
                - package_name: PyPI/pip package name
                - module_name: Python module where the plugin class is defined
                - human_name: display-friendly name
                - description: textual description or docstring
                - plugin_type: one of the plugin type identifiers (e.g., "tts", "stt", "wakeword", "audio")
                - url: source or homepage URL
                - class: plugin class name
        """
        self._data = data
        self._clazz = None
        self._plugtype = None

    @staticmethod
    def from_name(name: str) -> "OpenVoiceOSPlugin":
        """
        Create an OpenVoiceOSPlugin from an entry-point name by collecting discovered metadata.
        
        Searches installed plugin registries (STT, TTS, Wake Word, Audio) for the given entry-point name to infer plugin type, and attempts to load the plugin class to populate class name and description in the metadata.
        
        Parameters:
            name (str): Entry-point name of the plugin to look up.
        
        Returns:
            OpenVoiceOSPlugin: Instance populated with discovered metadata; the plugin may not be installed (its class may be None).
        """
        data = {"name": name}
        if name in find_stt_plugins():
            data["plugin_type"] = PluginTypes.STT
        elif name in find_tts_plugins():
            data["plugin_type"] = PluginTypes.TTS
        elif name in find_wake_word_plugins():
            data["plugin_type"] = PluginTypes.WAKEWORD
        elif name in find_audio_service_plugins():
            data["plugin_type"] = PluginTypes.AUDIO
        engine = load_plugin(name)
        if engine:
            data["class"] = engine.__name__
            data["description"] = engine.__doc__

        return OpenVoiceOSPlugin(data)

    @property
    def json(self) -> dict:
        """
        Serialize the plugin's metadata into a JSON-serializable dictionary.
        
        Returns:
            dict: Metadata dictionary with keys:
                - name: entry point name of the plugin or None
                - package_name: PyPI/package identifier or None
                - module_name: Python module containing the plugin class or None
                - human_name: human-friendly display name or None
                - description: textual description or docstring or None
                - plugin_type: PluginTypes value or None
                - url: source or project URL or None
                - is_installed: `True` if the plugin class can be imported, `False` otherwise
                - class: the uninstantiated plugin class object or None
        
            The returned dict is merged with any additional fields present in the plugin's internal data.
        """
        data = {
            "name": self.name,
            "package_name": self.package_name,
            "module_name": self.module_name,
            "human_name": self.human_name,
            "description": self.description,
            "plugin_type": self.plugin_type,
            "url": self.url,
            "is_installed": self.is_installed,
            "class": self.clazz
        }
        return merge_dict(data, self._data)

    @property
    def name(self) -> Optional[str]:
        """
        Plugin entry point name.
        
        Returns:
            name (Optional[str]): Entry point identifier (e.g. "ovos-stt-plugin-whisper") or None if not present.
        """
        return self._data.get("name")

    @property
    def package_name(self) -> Optional[str]:
        """
        PyPI/pip package name used to install the plugin (e.g. "ovos-stt-plugin-whisper").
        
        Returns:
            package_name (Optional[str]): The package name, or None if not specified.
        """
        return self._data.get("package_name")

    @property
    def module_name(self) -> Optional[str]:
        """
        Get the Python module where the plugin class is defined.
        
        If the plugin is installed and the module name is not already recorded, the value will be cached into the plugin's internal metadata.
        
        Returns:
            module_name (str): The module name (e.g. "ovos_stt_plugin_whisper"), or `None` if unknown.
        """
        if self.is_installed:
            if not self._data.get("module_name"):
                self._data["module_name"] = self._clazz.__module__
            return self._clazz.__module__
        return self._data.get("module_name")

    @property
    def human_name(self) -> Optional[str]:
        """
        Produce a human-readable display name for the plugin by deriving it from available metadata.
        
        The name is populated (if missing) in this order: the plugin class name (split from CamelCase), the package name, then the entry-point name (split from CamelCase). Hyphens and underscores are replaced with spaces and the result is title-cased; occurrences of "Tts" and "Stt" are normalized to "TTS" and "STT".
        
        Returns:
            human_name (Optional[str]): The derived display name, or `None` if no source is available.
        """
        if not self._data.get("human_name") and self.clazz:
            self._data["human_name"] = camel_case_split(self.clazz.__name__)
        if not self._data.get("human_name") and self.package_name:
            self._data["human_name"] = self.package_name
        if not self._data.get("human_name") and self.name:
            self._data["human_name"] = camel_case_split(self.name)
        # normalize it
        if self._data.get("human_name"):
            self._data["human_name"] = self._data["human_name"]\
                .replace("-", " ").replace("_", " ").title()\
                .replace("Tts", "TTS").replace("Stt", "STT")
        return self._data.get("human_name")

    @property
    def description(self) -> Optional[str]:
        """
        Get the plugin's textual description, preferring metadata and falling back to the plugin class docstring.
        
        Returns:
            description (str): The plugin description if available, otherwise `None`.
        """
        if not self._data.get("description") and self.clazz:
            self._data["description"] = self.clazz.__doc__
        return self._data.get("description")

    @property
    def plugin_type(self) -> Optional[PluginTypes]:
        """
        Infer the plugin's type as a PluginTypes value.
        
        Determination follows this order: explicit metadata, installed entry points, entry name heuristics, description text, package name, then module name.
        
        Returns:
            PluginTypes or None: The inferred plugin type, or `None` if it cannot be determined.
        """
        # check json data
        if not self._plugtype and self._data.get("plugin_type"):
            self._plugtype = self._data.get("plugin_type")
            if "tts" in self._plugtype.lower():
                self._plugtype = PluginTypes.TTS
            elif "stt" in self._plugtype.lower():
                self._plugtype = PluginTypes.STT
            elif "word" in self._plugtype.lower():
                self._plugtype = PluginTypes.WAKEWORD
            elif "audio" in self._plugtype.lower():
                self._plugtype = PluginTypes.AUDIO
            else:
                self._plugtype = None

        # check if installed
        if not self._plugtype and self.name:
            if self.name in find_stt_plugins():
                self._plugtype = PluginTypes.STT
            elif self.name in find_tts_plugins():
                self._plugtype = PluginTypes.TTS
            elif self.name in find_wake_word_plugins():
                self._plugtype = PluginTypes.WAKEWORD
            elif self.name in find_audio_service_plugins():
                self._plugtype = PluginTypes.AUDIO

        # parse name
        if not self._plugtype and self.name:
            if "tts" in self.name.lower():
                self._plugtype = PluginTypes.TTS
            elif "stt" in self.name.lower():
                self._plugtype = PluginTypes.STT
            elif "word" in self.name.lower():
                self._plugtype = PluginTypes.WAKEWORD
            elif "audio" in self.name.lower():
                self._plugtype = PluginTypes.AUDIO

        # parse description (use raw data to avoid circular dependency via clazz)
        _raw_desc = self._data.get("description") or ""
        if not self._plugtype and _raw_desc:
            if "tts" in _raw_desc.lower():
                self._plugtype = PluginTypes.TTS
            elif "stt" in _raw_desc.lower():
                self._plugtype = PluginTypes.STT
            elif "word" in _raw_desc.lower():
                self._plugtype = PluginTypes.WAKEWORD
            elif "audio" in _raw_desc.lower():
                self._plugtype = PluginTypes.AUDIO

        # parse package name
        if not self._plugtype and self.package_name:
            if "tts" in self.package_name.lower():
                self._plugtype = PluginTypes.TTS
            elif "stt" in self.package_name.lower():
                self._plugtype = PluginTypes.STT
            elif "word" in self.package_name.lower():
                self._plugtype = PluginTypes.WAKEWORD
            elif "audio" in self.package_name.lower():
                self._plugtype = PluginTypes.AUDIO

        # parse module name (use raw data to avoid circular dependency via clazz)
        _raw_module = self._data.get("module_name") or ""
        if not self._plugtype and _raw_module:
            if "tts" in _raw_module.lower():
                self._plugtype = PluginTypes.TTS
            elif "stt" in _raw_module.lower():
                self._plugtype = PluginTypes.STT
            elif "word" in _raw_module.lower():
                self._plugtype = PluginTypes.WAKEWORD
            elif "audio" in _raw_module.lower():
                self._plugtype = PluginTypes.AUDIO

        if not self._data.get("plugin_type"):
            self._data["plugin_type"] = self._plugtype
        return self._plugtype

    @property
    def url(self) -> Optional[str]:
        """Source URL (e.g. GitHub repository link)."""
        return self._data.get("url")

    @property
    def is_installed(self) -> bool:
        """
        Check whether the plugin package is installed and its class is importable.
        
        Returns:
            `true` if the plugin class can be imported, `false` otherwise.
        """
        return self.clazz is not None

    @property
    def clazz(self) -> Optional[Type]:
        """
        Return the uninstantiated plugin class for this plugin.
        
        Returns:
            plugin_class (Optional[Type]): The plugin class object if available, or `None` when the plugin cannot be imported or is not installed.
        """
        if not self._clazz and self.name:
            self._clazz = self.load()
        return self._clazz

    def load(self) -> Optional[Type]:
        """
        Import and return the plugin class specified by this plugin's entry point name.
        
        Returns:
            The plugin class (uninstantiated), or `None` if the plugin cannot be found.
        """
        return load_plugin(self.name, plug_type=self.plugin_type)

    def install(self) -> bool:
        """
        Install the plugin's Python package via pip.

        Uses the plugin's package_name when present; if absent and the plugin url points to GitHub, installs from "git+<url>". Returns False when neither an installable package_name nor a GitHub URL is available.

        Returns:
            True if installation succeeded, False if no install source is available.

        Raises:
            PipException: If pip exits with a non-zero status during installation.
        """
        if self.package_name:
            return pip_install([self.package_name])
        if self.url and "github" in self.url:
            return pip_install(["git+" + self.url])
        return False
