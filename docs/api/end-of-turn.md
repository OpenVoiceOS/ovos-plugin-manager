# End of Turn

Entry point group: **`opm.end_of_turn`**
Config entry point group: **`opm.end_of_turn.config`**
Template: `ovos_plugin_manager.templates.eot`

---

## `EndOfTurnEngine` base class

```python
from ovos_plugin_manager.templates.eot import EndOfTurnEngine
```

End-of-turn plugins decide whether the user has finished their turn, from the audio
stream alone. This is distinct from VAD: a VAD engine reports whether the current frame
contains speech, while an end-of-turn engine answers the higher-level question "is the
user done talking?" and keeps updating that answer as more audio arrives.

`ovos-dinkum-listener` uses an end-of-turn engine, when one is configured, to decide when
a command ends. Without one it falls back to its built-in silence timer.

### Constructor

```python
EndOfTurnEngine(config: Optional[dict] = None, sample_rate: Optional[int] = None)
```

| Attribute | Type | Default | Description |
|---|---|---|---|
| `sample_rate` | `int` | `16000` | Audio sample rate in Hz. |
| `threshold` | `float` | `0.5` | `p_end` above which the turn is considered finished. |
| `supported_langs` | `tuple[str, ...]` | `()` | Primary BCP-47 language subtags the engine supports; empty means all. |

### Method to implement

#### `get_probability(chunk: bytes, context: Optional[ChunkContext] = None) -> float`

Return the probability that the user has finished their turn, in `[0.0, 1.0]`. The base
class returns `0.0`, which means the engine never fires.

The engine is fed every chunk of microphone audio captured while a command may be in
progress. Chunks are not required to be any fixed size; the engine may re-frame them
internally. Audio is 16-bit signed PCM, mono, at `sample_rate`.

`context` carries what the listener already knows about the chunk, when it provides it.
An engine that decides from the raw audio ignores it; an engine that decides from speech
activity reads the listener's VAD verdict from it instead of running a second detector.
It is optional, so an engine stays self-contained and works with any caller.

### Provided methods

#### `update(chunk: bytes, context: Optional[ChunkContext] = None) -> EndOfTurnDecision`

Feed a chunk and return an `EndOfTurnDecision(p_end, p_speech, ended)`. `ended` is `True`
when `p_end >= threshold`.

#### `is_end_of_turn(chunk: bytes, context: Optional[ChunkContext] = None) -> bool`

Convenience wrapper that returns only the `ended` boolean.

#### `p_speech` (property)

Probability that the user is speaking, if the engine reports it; `None` otherwise.

#### `reset()`

Reset any internal state. Called when a new user turn starts.

#### `runtime_requirements` (classproperty)

Defaults to fully offline.

---

## `EndOfTurnDecision`

```python
from ovos_plugin_manager.templates.eot import EndOfTurnDecision
```

| Attribute | Type | Description |
|---|---|---|
| `p_end` | `float` | Probability the user has finished their turn. |
| `p_speech` | `Optional[float]` | Probability the user is speaking, or `None`. |
| `ended` | `bool` | Whether `p_end` crossed the threshold for this chunk. |

---

## `ChunkContext`

```python
from ovos_plugin_manager.templates.eot import ChunkContext
```

What the listener already knows about a chunk, when it offers it.

| Attribute | Type | Description |
|---|---|---|
| `is_speech` | `Optional[bool]` | The listener's VAD verdict for this chunk, or `None`. |

---

## Configuration

End-of-turn config is read from `ovos.conf` under `listener.end_of_turn`:

```json
{
  "listener": {
    "end_of_turn": {
      "module": "ovos-eot-plugin-cuelight",
      "ovos-eot-plugin-cuelight": {
        "model": "cuelight-nano",
        "preset": "careful"
      }
    }
  }
}
```

The built-in modules `dummy`, `none`, and `silence` all resolve to the no-op
`EndOfTurnEngine`, which never fires; a listener that loads one keeps its own
end-of-turn logic.

A plugin can declare `fallback_module` in its own config block; if the plugin fails to
load, the factory retries with the fallback module.

## Factory

```python
from ovos_plugin_manager.end_of_turn import OVOSEndOfTurnFactory

eot = OVOSEndOfTurnFactory.create()   # reads listener.end_of_turn from config
```

| Function | Purpose |
|---|---|
| `find_end_of_turn_plugins()` | `{name: entrypoint}` for installed plugins. |
| `load_end_of_turn_plugin(name)` | Load an uninstantiated plugin class. |
| `get_end_of_turn_configs()` | Valid plugin configurations by plugin name. |
| `get_end_of_turn_module_configs(name)` | Valid configurations for one plugin. |
| `get_end_of_turn_config(config)` | Resolve the plugin-specific config dict. |
