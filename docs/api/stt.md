# STT — Speech-to-Text

Entry point group: **`opm.stt`**
Config entry point group: **`opm.stt.config`**
Template: `ovos_plugin_manager.templates.stt`
Factory: `ovos_plugin_manager.stt.OVOSSTTFactory`

---

## Module-level helpers (`ovos_plugin_manager.stt`)

### `find_stt_plugins() -> dict`

Return a dict of `{entry_point_name: class}` for all installed STT plugins.

### `load_stt_plugin(module_name: str) -> Type[STT]`

Return the uninstantiated class for the named plugin.

### `get_stt_configs() -> dict`

Return `{plugin_name: {lang: [config_dicts]}}` for all installed STT plugins.

### `get_stt_module_configs(module_name: str) -> dict`

Return `{lang: [config_dicts]}` for a single plugin, sorted by priority.

### `get_stt_lang_configs(lang: str, include_dialects: bool = False) -> dict`

Return `{plugin_name: [sorted_configs]}` for all plugins that support `lang`.

### `get_stt_supported_langs() -> dict`

Return `{lang: [plugin_names]}` for all installed STT plugins.

### `get_stt_config(config: dict = None, module: str = None) -> dict`

Resolve merged STT config for the given module from the global configuration.
Equivalent to `get_plugin_config(config, "stt", module)`.
Raises `AssertionError` if `lang` is not present in the resolved config.

---

## `OVOSSTTFactory`

```python
from ovos_plugin_manager.stt import OVOSSTTFactory
```

### `OVOSSTTFactory.get_class(config=None) -> Type[STT]`

Return the STT class specified by `config['module']`.

### `OVOSSTTFactory.create(config=None) -> STT`

Instantiate and return an STT engine based on `config` (or the global config).
Raises on failure with a descriptive log.

---

## `STT` base class

```python
from ovos_plugin_manager.templates.stt import STT
```

### Constructor

```python
STT(config: Optional[dict] = None)
```

| Attribute | Type | Description |
|---|---|---|
| `config` | `dict` | Plugin-specific configuration dict. |
| `can_stream` | `bool` | `True` if this plugin supports streaming (set by `StreamingSTT`). |
| `lang` | `str` | Active language (BCP-47). Reads from config, then from the current Session. |

### Abstract methods (must implement)

#### `execute(audio: AudioData, language: Optional[str] = None) -> str`

Transcribe `audio` and return the best single transcription string.

#### `available_languages: Set[str]` (classproperty)

Return the set of BCP-47 language codes supported by this plugin.

### Provided methods (may override)

#### `transcribe(audio: AudioData, lang: Optional[str] = None) -> List[Tuple[str, float]]`

Return a list of `(transcription, confidence)` pairs. The default implementation wraps
`execute` and returns `[(text, 1.0)]`.

If `lang="auto"`, language detection is attempted via the bound `AudioLanguageDetector`
before calling `execute`.

#### `detect_language(audio, valid_langs=None) -> Tuple[str, float]`

Run language detection using the bound `AudioLanguageDetector`. Requires `bind()` to have
been called first. Raises `NotImplementedError` if no detector is bound.

#### `bind(detector: AudioLanguageDetector)`

Attach an `AudioLanguageDetector` for use in `detect_language` / auto-lang `transcribe`.

#### `runtime_requirements` (classproperty) -> `RuntimeRequirements`

Override to declare connectivity needs. Defaults to `RuntimeRequirements()` (internet not
required).

---

## `StreamingSTT` base class

Extends `STT`. Use when audio is fed incrementally as it arrives.

```python
from ovos_plugin_manager.templates.stt import StreamingSTT, StreamThread
```

### Constructor

```python
StreamingSTT(config: Optional[dict] = None)
```

Sets `can_stream = True` and creates `transcript_ready: Event`.

### Methods

#### `stream_start(language: Optional[str] = None)`

Start a new streaming session. Stops any existing stream, creates a new `Queue` and
`StreamThread`, and starts the thread.

#### `stream_data(data: bytes)`

Feed a raw audio chunk to the active stream thread's queue.

#### `stream_stop() -> Optional[str]`

Signal end-of-stream, wait for the thread to finish, and return the final transcription.

#### `create_streaming_thread() -> StreamThread` (abstract)

Return a new `StreamThread` instance. Implementations must create a thread that reads
from `self.queue` and stores its result in `self.stream.text`.

---

## `StreamThread` base class

```python
from ovos_plugin_manager.templates.stt import StreamThread
```

ABC for the worker thread used with `StreamingSTT`. Subclass and implement
`handle_audio_stream`.

### `handle_audio_stream(audio: Generator, language: str)` (abstract)

Process the audio stream and store the final transcription in `self.text`.

---

## Configuration

STT config is read from `ovos.conf` under the `stt` key:

```json
{
  "stt": {
    "module": "ovos-stt-plugin-whisper",
    "lang": "en-US",
    "ovos-stt-plugin-whisper": {
      "model": "base"
    }
  }
}
```
