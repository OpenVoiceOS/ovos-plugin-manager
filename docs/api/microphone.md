# Microphone Plugins

**Entry point group:** `opm.microphone`
**Template:** `ovos_plugin_manager.templates.microphone`
**Factory:** `ovos_plugin_manager.microphone`

Microphone plugins provide a raw audio stream to `ovos-dinkum-listener`. They abstract
over different audio sources: ALSA, PulseAudio, network streams, files, etc.

---

## `OVOSMicrophone` base class

```python
from ovos_plugin_manager.templates.microphone import OVOSMicrophone
```

### Constructor

```python
OVOSMicrophone(config: Optional[dict] = None)
```

| Attribute | Type | Description |
|---|---|---|
| `sample_rate` | `int` | Samples per second (default 16000). |
| `sample_width` | `int` | Bytes per sample (default 2 = 16-bit). |
| `sample_channels` | `int` | Number of channels (default 1 = mono). |
| `chunk_size` | `int` | Bytes per read call (default 4096). |

### Abstract methods (must implement)

#### `open()`

Open the audio source and prepare for reading.

#### `close()`

Release the audio source.

#### `read_chunk() -> Optional[bytes]`

Return the next chunk of raw PCM audio bytes, or `None` if no data is available.

### Provided methods

#### `__enter__() / __exit__()`

Context manager support — calls `open()` / `close()`.

---

## Module-level helpers

```python
from ovos_plugin_manager.microphone import (
    find_microphone_plugins,
    load_microphone_plugin,
    get_microphone_config,
    OVOSMicrophoneFactory,
)
```

### `find_microphone_plugins() -> dict`

Return `{entry_point_name: class}` for all installed microphone plugins.

### `load_microphone_plugin(module_name: str) -> Type[OVOSMicrophone]`

Return the uninstantiated class.

### `get_microphone_config(config: dict = None) -> dict`

Resolve microphone config from the global configuration (`listener.microphone` section).

### `OVOSMicrophoneFactory.create(config=None) -> OVOSMicrophone`

Instantiate and return a microphone based on configuration.

---

## Configuration

```json
{
  "listener": {
    "microphone": {
      "module": "ovos-microphone-plugin-alsa",
      "ovos-microphone-plugin-alsa": {
        "device": "default",
        "sample_rate": 16000
      }
    }
  }
}
```
