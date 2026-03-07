# Writing an OVOS Plugin

This guide shows how to package a new OVOS plugin from scratch using `setup.py`.

## 1. Implement the base class

Choose the appropriate template from `ovos_plugin_manager.templates.*` and subclass it.

### Example: STT plugin

```python
# my_stt_plugin/__init__.py
from ovos_plugin_manager.templates.stt import STT
from ovos_plugin_manager.utils.audio import AudioData
from typing import Optional, Set


class MySTTPlugin(STT):
    """My custom speech-to-text engine."""

    @property
    def available_languages(cls) -> Set[str]:
        return {"en-US", "en-GB", "de-DE"}

    def execute(self, audio: AudioData, language: Optional[str] = None) -> str:
        lang = language or self.lang
        # call your backend here and return transcript
        return "hello world"
```

### Example: TTS plugin

```python
# my_tts_plugin/__init__.py
from ovos_plugin_manager.templates.tts import TTS, TTSValidator
from typing import Set


class MyTTSPlugin(TTS):
    """My custom text-to-speech engine."""

    def __init__(self, config=None):
        super().__init__(config, audio_ext="wav")

    @property
    def available_languages(cls) -> Set[str]:
        return {"en-US"}

    def get_tts(self, sentence: str, wav_file: str, lang=None, voice=None):
        # synthesize `sentence` to `wav_file`; return (wav_file, phonemes_or_None)
        return wav_file, None


class MyTTSValidator(TTSValidator):
    def validate_lang(self):
        assert self.tts.lang in MyTTSPlugin.available_languages

    def get_tts_class(self):
        return MyTTSPlugin
```

### Example: Wake Word plugin

```python
# my_ww_plugin/__init__.py
from ovos_plugin_manager.templates.hotwords import HotWordEngine


class MyWakeWord(HotWordEngine):
    """My custom wake word detector."""

    def __init__(self, key_phrase="hey mycroft", config=None):
        super().__init__(key_phrase, config)
        # load your model here

    def update(self, chunk: bytes):
        # feed audio chunk to the model
        pass

    def found_wake_word(self) -> bool:
        # return True when wake word is detected
        return False
```

## 2. Expose the plugin via `setup.py`

Register your class under the correct entry point group so OPM can discover it.

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="ovos-stt-plugin-my-engine",
    version="0.1.0",
    author="Your Name",
    url="https://github.com/your-org/ovos-stt-plugin-my-engine",
    license="Apache-2.0",
    packages=find_packages(),
    install_requires=["ovos-plugin-manager>=0.0.1"],
    entry_points={
        # STT plugin
        "opm.stt": [
            "my-engine-stt = my_stt_plugin:MySTTPlugin"
        ],
        # Optional: expose supported-language configurations
        "opm.stt.config": [
            "my-engine-stt = my_stt_plugin:MySTTPluginConfig"
        ],
    },
)
```

Replace `opm.stt` with the appropriate entry point group for your plugin type.
See [Plugin Types](plugin-types.md) for the full list.

## 3. Install during development

```bash
pip install -e .
```

The plugin is now discoverable by OPM without any additional registration:

```python
from ovos_plugin_manager.stt import find_stt_plugins, load_stt_plugin
print("my-engine-stt" in find_stt_plugins())  # True
MySTT = load_stt_plugin("my-engine-stt")
```

## 4. Expose language configurations (optional)

Plugins that support multiple voices/languages/models should expose a `.config` entry
point returning a dict of `{lang: [list_of_config_dicts]}`. Each config dict represents
one voice/model variant and can include:

| Key | Type | Description |
|---|---|---|
| `lang` | `str` | BCP-47 language code |
| `priority` | `int` | Lower = higher priority (default 60) |
| `gender` | `str` | `"male"` or `"female"` |
| `offline` | `bool` | Whether the variant works without internet |
| `display_name` | `str` | Human-readable name for the voice/model |

```python
class MyTTSPluginConfig:
    """Advertise supported languages and voices."""

    @staticmethod
    def get_configs():
        return {
            "en-US": [
                {"lang": "en-US", "gender": "female", "priority": 50, "offline": True},
                {"lang": "en-US", "gender": "male",   "priority": 50, "offline": True},
            ],
            "de-DE": [
                {"lang": "de-DE", "gender": "female", "priority": 60, "offline": False},
            ],
        }
```

## 5. `RuntimeRequirements`

Override `runtime_requirements` to declare connectivity needs. OVOS uses this to decide
whether the plugin can be loaded before network/internet is available.

```python
from ovos_utils.process_utils import RuntimeRequirements

class MySTTPlugin(STT):

    @classproperty
    def runtime_requirements(cls):
        # This plugin needs internet at startup
        return RuntimeRequirements(
            internet_before_load=True,
            network_before_load=True,
            requires_internet=True,
            requires_network=True,
            no_internet_fallback=False,
            no_network_fallback=False,
        )
```

For a fully offline plugin, all values are `False` / `True` as appropriate.

## 6. PHAL plugins

PHAL plugins run as daemon threads and receive bus events. See [PHAL reference](api/phal.md).

```python
from ovos_plugin_manager.templates.phal import PHALPlugin, PHALValidator


class MyPHALPlugin(PHALPlugin):
    """Hardware integration for MyDevice."""

    def on_record_begin(self, message=None):
        # light up LED when listening starts
        pass

    def run(self):
        # main daemon loop
        while True:
            pass
```

```python
# setup.py entry_points
"opm.phal": ["my-phal-plugin = my_phal:MyPHALPlugin"]
```
