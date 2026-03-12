# Wake Word / Hotword

Entry point group: **`opm.wake_word`**
Config entry point group: **`opm.wake_word.config`**
Verifier entry point group: **`opm.wake_word.verifier`**
Template: `ovos_plugin_manager.templates.hotwords`
Factory: `ovos_plugin_manager.wakewords.OVOSWakeWordFactory`

---

## Module-level helpers (`ovos_plugin_manager.wakewords`)

### `find_wake_word_plugins() -> dict`

Return `{entry_point_name: class}` for all installed wake word plugins.

### `load_wake_word_plugin(module_name: str) -> Type[HotWordEngine]`

Return the uninstantiated class for the named plugin.

### `find_wake_word_verifier_plugins() -> dict`

Return all installed wake word verifier plugins.

### `load_wake_word_verifier_plugin(module_name: str) -> Type[HotWordVerifier]`

Return the uninstantiated verifier class.

### `get_ww_configs() -> dict`

Return `{plugin_name: [config_dicts]}` for all installed wake word plugins.

### `get_ww_module_configs(module_name: str) -> dict`

Return configurations for a single plugin.

### `get_ww_lang_configs(lang: str, include_dialects: bool = False) -> dict`

Return `{plugin_name: [configs]}` for all plugins that support `lang`.

### `get_ww_supported_langs() -> dict`

Return `{lang: [plugin_names]}`.

### `get_hotwords_config(config: dict = None) -> dict`

Return the `hotwords` section of the global config (or `config` if provided).

### `get_ww_id(plugin_name: str, ww_name: str, ww_config: dict) -> str`

Return a stable unique identifier for a specific wake word configuration.

---

## `OVOSWakeWordFactory`

```python
from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
```

### `OVOSWakeWordFactory.get_class(hotword: str, config: Optional[dict] = None) -> type`

Return the plugin class configured for `hotword`. Falls back to base `HotWordEngine` if
the hotword is not found in config.

### `OVOSWakeWordFactory.load_module(module: str, hotword: str, hotword_config: dict) -> HotWordEngine`

Instantiate and return a `HotWordEngine` for `hotword` using `module`.

### `OVOSWakeWordFactory.create_hotword(hotword: str = "hey mycroft", config: Optional[dict] = None) -> HotWordEngine`

High-level method: look up `hotword` in config, load its module, return an initialized
engine. On failure, attempts the `fallback_ww` configured for the hotword.

---

## `HotWordEngine` base class

```python
from ovos_plugin_manager.templates.hotwords import HotWordEngine
```

### Constructor

```python
HotWordEngine(key_phrase: str, config: Optional[Dict[str, Any]] = None)
```

| Attribute | Type | Description |
|---|---|---|
| `key_phrase` | `str` | Lower-cased string representation of the wake word. |
| `config` | `dict` | Plugin config from `Configuration()['hotwords'][key_phrase]`. |

### Abstract methods (must implement)

#### `update(chunk: bytes)`

Feed a raw audio chunk to the engine. The engine should update its internal detection state.

#### `found_wake_word() -> bool`

Return `True` if the wake word has been detected. Should reset internal state after detection.

### Provided methods (may override)

#### `reset()`

Reset the engine state in preparation for a new detection cycle.

#### `stop() / shutdown()`

Release model resources and shut down the engine.

#### `runtime_requirements` (classproperty)

Defaults to fully offline (`internet_before_load=False`, etc.).

---

## `HotWordVerifier` base class

```python
from ovos_plugin_manager.templates.hotwords import HotWordVerifier
```

Verifier plugins are called after a wake word is detected to filter false positives.

### Constructor

```python
HotWordVerifier(config: Optional[Dict[str, Any]] = None)
```

### Abstract method

#### `verify(chunk: bytes) -> bool`

Return `True` if the audio chunk contains a genuine wake word activation.

---

## Configuration

Wake word configuration lives under the `hotwords` key:

```json
{
  "hotwords": {
    "hey mycroft": {
      "module": "ovos-ww-plugin-openwakeword",
      "model": "hey_mycroft",
      "listen": true,
      "fallback_ww": "hey_mycroft_precise"
    },
    "hey_mycroft_precise": {
      "module": "ovos-ww-plugin-precise-lite",
      "model_file": "hey-mycroft.tflite"
    }
  }
}
```

Unlike STT/TTS, the `hotwords` section is keyed by wake word name rather than module
name, and each entry includes a `module` key identifying the plugin.
