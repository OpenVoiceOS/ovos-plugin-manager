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
| `dispatch_template` | `(template, skill_id, data, session_id="default", index=0, page_count=1)` (below) |
| `on_legacy_page` | `(skill_id, page, data, session_id="default", index=0, page_count=1)` (below) |

### Active entry: `index` and `page_count`

`dispatch_template` and `on_legacy_page` get two more arguments, as
[6.3](https://github.com/OpenVoiceOS/architecture/blob/b6c1583/gui-1.md#63-events-received)
(proposed amendment B) defines them:

- `index`: the active entry's zero-based position in `page_names`.
- `page_count`: the length of `page_names`.

The service sends them on every show and again when a
[`gui.page.focus`](https://github.com/OpenVoiceOS/architecture/blob/b6c1583/gui-1.md#42-messages)
makes another held entry active. That second dispatch, with the new `index`, is how a
render backend learns that the focus took effect. A backend that does not have both values
for a namespace must not send `gui.page.focus` for it.

The defaults (`0` and `1`) keep an adapter working that ignores them. The `handle_show_*`
handlers do not get them; an adapter that needs them overrides `dispatch_template`.

### Legacy page hook

```python
on_legacy_page(skill_id: str, page: str, data: Dict[str, Any], session_id: str = "default",
               index: int = 0, page_count: int = 1) -> None
```

A skill that shows its own page name (`time`, `CurrentWeather`, `Timer`) instead of a
`SYSTEM_*` template is not dispatched as a template. OVOS-GUI-1
[4.2](https://github.com/OpenVoiceOS/architecture/blob/b6c1583/gui-1.md#42-messages) forbids
that, and allows a deployment-specific legacy path instead. `on_legacy_page` is that path.

- The service takes this path when the **first** `page_names` entry is not a `SYSTEM_*`
  name, as 4.2 decides. `page` is the **active** entry, exactly as the skill sent it. The
  service calls the hook once per show, the same as `dispatch_template`, with the same
  `index` and `page_count`.
- `data` is the namespace's full merged session data, with `__` keys stripped and null
  values removed, the same map `dispatch_template` gets.
- The order is the template order: `on_session_update`, then `on_legacy_page`, then
  `on_namespace_activated`. Clear, removal and idle work the same as for a template.
- Legacy frame names that alias to a spec template (`SYSTEM_TextFrame` → `SYSTEM_text`)
  are dispatched as templates, not sent here.
- The default is a no-op. An adapter that cannot render skill pages ignores it.

This is the optional, transitional legacy-page hook of the proposed amendment E (branch
`gui1/legacy-page-hook`). A producer that relies on it is not conformant. It lets stock
skills keep rendering while they migrate to templates.

`handle_show_media_player` renders the unified media player from the `media_*` session keys
of the [3.4](https://github.com/OpenVoiceOS/architecture/blob/b6c1583/gui-1.md#34-catalogue)
catalogue (`media_title`, `media_artist`, `media_album`, `media_image`, `media_uri`,
`media_position`, `media_duration`, `media_playback_state`, `media_playlist`,
`media_search_results`, `media_playlist_position`).

`on_status_event` gets the topics of
[5.3](https://github.com/OpenVoiceOS/architecture/blob/b6c1583/gui-1.md#53-system-wide-signals)
(`ovos.listener.wakeword`, `ovos.utterance.speak`, …), the `gui.ambient.*` topics, and any
legacy topic the service still forwards.

The three interactive companions of the proposed amendment A, `SYSTEM_confirm`,
`SYSTEM_select` and `SYSTEM_input`, dispatch to `handle_show_confirm`,
`handle_show_select` and `handle_show_input`.

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
