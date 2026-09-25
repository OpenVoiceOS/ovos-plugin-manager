# PHAL — Platform/Hardware Abstraction Layer

Entry point group: **`opm.phal`**
Admin entry point group: **`opm.phal.admin`**
Template: `ovos_plugin_manager.templates.phal`

PHAL plugins are daemon threads that integrate OVOS with platform-specific hardware
(LEDs, fans, buttons, display panels, etc.). They receive bus events and can emit their
own bus messages.

---

## `PHALPlugin` base class

```python
from ovos_plugin_manager.templates.phal import PHALPlugin
```

Extends `threading.Thread` with `daemon=True`.

### Constructor

```python
PHALPlugin(bus=None, name: str = "", config: Optional[dict] = None)
```

On init the plugin automatically:
1. Reads config from `Configuration()['PHAL'][name]` (or uses `config` if provided).
2. Registers all core bus event handlers (audio, enclosure, eyes, mouth).
3. Calls `start()` to begin the daemon thread.

| Attribute | Type | Description |
|---|---|---|
| `bus` | `MessageBusClient` | OVOS message bus connection. |
| `name` | `str` | Plugin identifier (used in bus event namespacing). |
| `config` | `dict` | Plugin-specific configuration. |
| `log` | `Logger` | Logger instance. |

### Lifecycle

#### `run()`

Override to implement the plugin's main loop. Called automatically after `start()`.

#### `shutdown()`

Unregister all bus event handlers and stop the daemon thread. Called by OVOS on service
shutdown.

### Bus event handlers (all optional to override)

All handlers receive a `Message` argument.

#### Audio events

| Handler | Bus message |
|---|---|
| `on_record_begin` | `recognizer_loop:record_begin` |
| `on_record_end` | `recognizer_loop:record_end` |
| `on_audio_output_start` | `recognizer_loop:audio_output_start` |
| `on_audio_output_end` | `recognizer_loop:audio_output_end` |
| `on_awake` | `mycroft.awoken` |
| `on_sleep` | `recognizer_loop:sleep` |
| `on_speak` | `speak` |

#### System events

| Handler | Bus message |
|---|---|
| `on_reset` | `enclosure.reset` |
| `on_no_internet` | `enclosure.notify.no_internet` |
| `on_system_reset` | `enclosure.system.reset` |
| `on_system_mute` | `enclosure.system.mute` |
| `on_system_unmute` | `enclosure.system.unmute` |
| `on_system_blink` | `enclosure.system.blink` |

#### Eye events

| Handler | Bus message |
|---|---|
| `on_eyes_on` | `enclosure.eyes.on` |
| `on_eyes_off` | `enclosure.eyes.off` |
| `on_eyes_blink` | `enclosure.eyes.blink` |
| `on_eyes_narrow` | `enclosure.eyes.narrow` |
| `on_eyes_look` | `enclosure.eyes.look` |
| `on_eyes_color` | `enclosure.eyes.color` |
| `on_eyes_brightness` | `enclosure.eyes.level` |
| `on_eyes_volume` | `enclosure.eyes.volume` |
| `on_eyes_spin` | `enclosure.eyes.spin` |
| `on_eyes_timed_spin` | `enclosure.eyes.timedspin` |
| `on_eyes_reset` | `enclosure.eyes.reset` |
| `on_eyes_set_pixel` | `enclosure.eyes.setpixel` |
| `on_eyes_fill` | `enclosure.eyes.fill` |

#### Mouth / display events

| Handler | Bus message |
|---|---|
| `on_display_reset` | `enclosure.mouth.reset` |
| `on_talk` | `enclosure.mouth.talk` |
| `on_think` | `enclosure.mouth.think` |
| `on_listen` | `enclosure.mouth.listen` |
| `on_smile` | `enclosure.mouth.smile` |
| `on_viseme` | `enclosure.mouth.viseme` |
| `on_viseme_list` | `enclosure.mouth.viseme_list` |
| `on_text` | `enclosure.mouth.text` |
| `on_display` | `enclosure.mouth.display` |
| `on_weather_display` | `enclosure.weather.display` |

### Helper methods

#### `emit(msg_type: str, msg_data: Optional[dict] = None)`

Emit a bus message scoped to this plugin: `ovos.PHAL.<name>.<msg_type>`.

#### `mouth_events_active: bool` (property)

Whether mouth/viseme events are currently enabled.

---

## `PHALValidator`

```python
from ovos_plugin_manager.templates.phal import PHALValidator
```

Called before a PHAL plugin is loaded. Return `False` to prevent loading
(e.g. on unsupported hardware).

```python
class PHALValidator:
    @staticmethod
    def validate(config: dict = None) -> bool:
        ...
```

Assign your validator class to `PHALPlugin.validator`:

```python
class MyPHALPlugin(PHALPlugin):
    validator = MyPHALValidator
```

The default validator returns `True` unless `config['enabled']` is explicitly `False`.

---

## `AdminPlugin` / `AdminValidator`

Identical to `PHALPlugin` / `PHALValidator` but registered under the `opm.phal.admin`
entry point. Admin plugins may run with elevated privileges.

---

## Configuration

```json
{
  "PHAL": {
    "my-phal-plugin": {
      "enabled": true,
      "some_setting": "value"
    }
  }
}
```

The `enabled` key is checked by the default `PHALValidator`. Set to `false` to disable
a plugin without uninstalling it.
