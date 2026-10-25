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
partial implementations are valid.

| Handler | Arguments |
|---|---|
| `handle_show_<template>` (`handle_show_text`, `handle_show_weather`, …), called by `dispatch_template` | `(skill_id, data, session_id="default")` |
| `on_session_update` | `(skill_id, data, session_id="default")` |
| `on_namespace_activated`, `on_namespace_deactivated` | `(skill_id, session_id="default")` |
| `on_idle` | `(session_id="default")`: the session whose stack emptied. Idle is per session. |
| `on_status_event` | `(event_name, data, session_id="default")`: `session_id` is the session that raised it. |
| `on_legacy_page` | `(skill_id, page, data, session_id="default")` (below) |

### Legacy page hook

```python
on_legacy_page(skill_id: str, page: str, data: Dict[str, Any], session_id: str = "default") -> None
```

A skill that shows its own page name (`time`, `CurrentWeather`, `Timer`) instead of a
`SYSTEM_*` template is not dispatched as a template. OVOS-GUI-1
[4.2](https://github.com/OpenVoiceOS/architecture/blob/b6c1583/gui-1.md#42-messages) forbids
that, and allows a deployment-specific legacy path instead. `on_legacy_page` is that path.

- `page` is the skill's own page name as sent. The service calls the hook once per show,
  for the active `page_names` entry only, the same as `dispatch_template`.
- `data` is the namespace's full merged session data, with `__` keys stripped and null
  values removed, the same map `dispatch_template` gets.
- The order is the template order: `on_session_update`, then `on_legacy_page`, then
  `on_namespace_activated`. Clear, removal and idle work the same as for a template.
- Legacy frame names that alias to a spec template (`SYSTEM_TextFrame` → `SYSTEM_text`)
  are dispatched as templates, not sent here.
- The default is a no-op. An adapter that cannot render skill pages ignores it.

This hook is outside the specification. It lets stock skills keep rendering while they
migrate to templates.

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
