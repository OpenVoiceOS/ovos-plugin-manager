# VAD — Voice Activity Detection

Entry point group: **`opm.VAD`**
Config entry point group: **`opm.VAD.config`**
Template: `ovos_plugin_manager.templates.vad`

---

## `VADEngine` base class

```python
from ovos_plugin_manager.templates.vad import VADEngine
```

VAD plugins determine whether a given audio segment contains speech. They are used by
`ovos-dinkum-listener` to trim leading/trailing silence before STT.

### Constructor

```python
VADEngine(config: Optional[dict] = None, sample_rate: Optional[int] = None)
```

| Attribute | Type | Default | Description |
|---|---|---|---|
| `sample_rate` | `int` | `16000` | Audio sample rate in Hz. |
| `padding_duration_ms` | `int` | `300` | Ring buffer duration in ms. |
| `frame_duration_ms` | `int` | `30` | Frame size in ms. |
| `thresh` | `float` | `0.8` | Fraction of voiced frames needed to trigger speech detection. |
| `num_padding_frames` | `int` | derived | `padding_duration_ms / frame_duration_ms`. |

### Abstract method (must implement)

#### `is_silence(chunk: bytes) -> bool`

Return `True` if the provided audio chunk does not contain speech.

### Provided methods

#### `extract_speech(audio: bytes) -> bytes`

Remove leading and trailing silence from `audio` using a sliding ring-buffer algorithm.
Returns only the voiced portion of the audio.

#### `reset()`

Reset any internal state. Called between utterances.

#### `runtime_requirements` (classproperty)

Defaults to fully offline.

---

## `AudioFrame`

```python
from ovos_plugin_manager.templates.vad import AudioFrame
```

Data class representing a single frame of audio.

| Attribute | Type | Description |
|---|---|---|
| `bytes` | `bytes` | Raw PCM audio data. |
| `timestamp` | `float` | Start time of the frame in seconds. |
| `duration` | `int` | Duration of the frame in seconds. |

---

## Configuration

VAD config is read from `ovos.conf` under `listener.VAD`:

```json
{
  "listener": {
    "VAD": {
      "module": "ovos-vad-plugin-silero",
      "ovos-vad-plugin-silero": {
        "thresh": 0.5,
        "padding_duration_ms": 400
      }
    }
  }
}
```
