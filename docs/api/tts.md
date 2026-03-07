# TTS — Text-to-Speech

Entry point group: **`opm.tts`**
Config entry point group: **`opm.tts.config`**
Template: `ovos_plugin_manager.templates.tts`
Factory: `ovos_plugin_manager.tts.OVOSTTSFactory`

---

## Module-level helpers (`ovos_plugin_manager.tts`)

### `find_tts_plugins() -> dict`

Return `{entry_point_name: class}` for all installed TTS plugins.

### `load_tts_plugin(module_name: str) -> Type[TTS]`

Return the uninstantiated class for the named plugin.

### `get_tts_configs() -> dict`

Return `{plugin_name: {lang: [config_dicts]}}` for all installed TTS plugins.

### `get_tts_module_configs(module_name: str) -> dict`

Return `{lang: [config_dicts]}` for a single plugin, sorted by priority.

### `get_tts_lang_configs(lang: str, include_dialects: bool = False) -> dict`

Return `{plugin_name: [sorted_configs]}` for all plugins that support `lang`.

### `get_tts_supported_langs() -> dict`

Return `{lang: [plugin_names]}` for all installed TTS plugins.

### `get_tts_config(config: dict = None, module: str = None) -> dict`

Resolve merged TTS config for the given module from the global configuration.

### `get_voice_id(plugin_name: str, lang: str, tts_config: dict) -> str`

Return a stable unique identifier for a specific voice configuration, composed of
`plugin_name`, `lang`, and an MD5 hash of the sorted config dict.

### `scan_voices() -> dict`

Iterate all installed TTS plugins, enumerate their voice configs, and write each to an
XDG-compliant JSON file under `~/.local/share/OPM/voice_configs/<lang>/`. Returns a dict
of `{voice_id: config_dict}`.

### `get_voices(scan: bool = False) -> dict`

Return all previously scanned voices from disk. If `scan=True`, re-scans first.

---

## `OVOSTTSFactory`

```python
from ovos_plugin_manager.tts import OVOSTTSFactory
```

### `OVOSTTSFactory.get_class(config=None) -> Type[TTS]`

Return the TTS class specified by `config['module']`. Defaults to
`ovos-tts-plugin-dummy` if no module is configured.

### `OVOSTTSFactory.create(config=None) -> TTS`

Instantiate and return a validated TTS engine. Calls `validator.validate()` before
returning. Raises `ValueError` if `module` is not set, or `RuntimeError` if the plugin
cannot be loaded.

---

## `TTS` base class

```python
from ovos_plugin_manager.templates.tts import TTS
```

### Constructor

```python
TTS(
    config: Optional[dict] = None,
    validator: Optional[TTSValidator] = None,
    audio_ext: str = "wav",
    phonetic_spelling: bool = True,
    ssml_tags: Optional[list] = None,
)
```

| Attribute | Type | Description |
|---|---|---|
| `config` | `dict` | Plugin-specific config. |
| `lang` | `str` | Active language (BCP-47). |
| `voice` | `str` | Active voice name (from `config['voice']`). |
| `audio_ext` | `str` | Output audio format extension (e.g. `"wav"`, `"mp3"`). |
| `ssml_tags` | `list` | SSML tags supported by this engine. |
| `enable_cache` | `bool` | Whether synthesis results are cached on disk. |
| `spellings` | `dict` | Phonetic spelling overrides loaded from `locale/` dir. |
| `queue` | `Queue` | Class-level playback queue (shared across instances). |
| `playback` | `PlaybackThread` | Class-level playback thread (set by `init()`). |

### Abstract methods (must implement)

#### `get_tts(sentence: str, wav_file: str, lang=None, voice=None) -> Tuple[str, Optional[str]]`

Synthesize `sentence` to `wav_file`. Returns `(wav_file_path, phonemes_or_None)`.
`lang` and `voice` default to `self.lang` and `self.voice`.

#### `available_languages: Set[str]` (classproperty)

Return BCP-47 codes supported by this plugin.

### Provided methods (may override)

#### `preprocess_sentence(sentence: str) -> List[str]`

Tokenize the sentence into chunks suitable for synthesis. Defaults to
`quebra_frases.sentence_tokenize` when `config['sentence_tokenize']` is `True`.

#### `synth(sentence: str, ctxt: TTSContext = None, **kwargs) -> Tuple[AudioFile, Optional[str]]`

Synthesize one chunk. Checks the disk cache first; falls back to `get_tts`. Result is
cached if `enable_cache` is `True`.

#### `execute(sentence, ident=None, listen=False, **kwargs)`

Full pipeline: SSML validation → preprocessing → `synth` per chunk → queue for playback.
Called by `ovos-audio`; not used in standalone / direct `get_tts` usage.

#### `viseme(phonemes: str) -> list`

Convert a phoneme string (`"p:0.1 AH:0.15 ..."`) to a list of
`(viseme_code, duration)` tuples for mouth animations.

#### `validate_ssml(utterance: str) -> str`

Strip or rewrite SSML tags not supported by this engine. Returns cleaned utterance.

#### `init(bus, playback)`

Connect TTS to `PlaybackThread` from `ovos-audio`. Must be called before `execute`.

#### `stop() / shutdown()`

Stop playback and release resources.

---

## `TTSContext`

```python
from ovos_plugin_manager.templates.tts import TTSContext
```

Represents the per-request synthesis context (plugin, language, voice, kwargs).
Manages a per-context disk cache (`TextToSpeechCache`).

### Constructor

```python
TTSContext(plugin_id: str, lang: str, voice: str, synth_kwargs: dict = None)
```

### Properties

- `tts_id: str` — unique path-like identifier `plugin_id/voice/lang`
- `get_cache(audio_ext, cache_config) -> TextToSpeechCache`
- `get_from_cache(sentence, audio_ext, cache_config) -> Tuple[AudioFile, Optional[phonemes]]`

---

## `TTSValidator`

```python
from ovos_plugin_manager.templates.tts import TTSValidator
```

Validates a TTS plugin after instantiation. Override in your plugin.

### Methods (all optional to override)

- `validate_dependencies()` — check external deps
- `validate_lang()` — confirm the configured language is supported
- `validate_connection()` — check that the backend is reachable
- `get_tts_class()` — return the associated TTS class (used for type checks)

---

## `StreamingTTS`

```python
from ovos_plugin_manager.templates.tts import StreamingTTS
```

Extends `TTS`. Use when the backend yields audio chunks as they are generated.

### Abstract method

#### `async stream_tts(sentence: str, **kwargs) -> AsyncIterable[bytes]`

Yield raw audio bytes for `sentence` as they become available.

### Provided methods

#### `async generate_audio(sentence, wav_file, play_streaming=True, listen=False, message=None, plugin_kwargs=None) -> str`

Stream TTS to file and optionally play in real time via `StreamingTTSCallbacks`.

#### `get_tts(sentence, wav_file, **kwargs) -> Tuple[str, None]`

Synchronous wrapper around `generate_audio` for non-streaming usage.

---

## `ConcatTTS`

```python
from ovos_plugin_manager.templates.tts import ConcatTTS
```

TTS that assembles audio from pre-recorded word/phoneme files using `sox`.

### Abstract method

#### `sentence_to_files(sentence) -> Tuple[List[str], List[str]]`

Return `(list_of_audio_files, list_of_phoneme_strings)` for `sentence`.

---

## Configuration

```json
{
  "tts": {
    "module": "ovos-tts-plugin-piper",
    "ovos-tts-plugin-piper": {
      "voice": "en_US-amy-medium",
      "enable_cache": true,
      "sentence_tokenize": true
    }
  }
}
```
