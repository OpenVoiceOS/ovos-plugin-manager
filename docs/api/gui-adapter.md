# GUI Adapter Plugins

**Entry point group:** `opm.gui_adapter`
**Template:** `ovos_plugin_manager.templates.gui.AbstractGUIPlugin`

GUI adapter plugins are the *rendering backends* (Qt, browser, TUI, …) that `ovos-gui`
loads. Unlike the single `GUIExtension` (one per device), adapters are **additive**: every
installed adapter is instantiated at once so a device can drive multiple displays
concurrently. `ovos-gui` dispatches each template event to all of them.

---

## `AbstractGUIPlugin` base class

```python
from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
```

```python
AbstractGUIPlugin(config: Dict[str, Any], bus: Optional[MessageBusClient] = None)
```

Subclass and override only the handlers you need — every handler defaults to a no-op, so
partial implementations are valid. Handlers cover the template events (`handle_show_idle`,
`handle_show_text`, `handle_show_list`, `handle_show_media_player`, `handle_show_weather`,
…) plus lifecycle hooks (`on_namespace_activated`, `on_namespace_deactivated`, `on_idle`)
and `on_status_event`. Each handler receives `(skill_id, data, session_id="default")`.

`handle_show_media_player` renders the OCP unified player from the `ocp_*` session keys
(title/artist/image, `ocp_uri`, `ocp_position`, `ocp_duration`, `ocp_playback_state`,
`ocp_playlist`, `ocp_search_results`, `ocp_playlist_position`).

---

## Discovery / loading helpers

```python
from ovos_plugin_manager.gui import (
    find_gui_adapter_plugins,     # {name: class}
    load_gui_adapter_plugin,      # name -> class
    OVOSGUIAdapterFactory,        # .create_all(bus, config) -> [AbstractGUIPlugin]
)
```

`OVOSGUIAdapterFactory.create_all()` instantiates every installed adapter; a failing
adapter is logged and skipped (one bad adapter never blocks the others or the GUI
service), and a headless device with no adapters yields an empty list.

---

## Spec conformance

Implements **OVOS-GUI-1**. Defines the `AbstractGUIPlugin` base and the
`opm.gui_adapter` plugin type (`PluginTypes.GUI_ADAPTER` /
`PluginConfigTypes.GUI_ADAPTER`) that `ovos-gui` uses to obtain its render backends.
Adapters are additive and event-driven: the GUI service broadcasts the spec's template
and status events, and every loaded adapter renders them independently.
