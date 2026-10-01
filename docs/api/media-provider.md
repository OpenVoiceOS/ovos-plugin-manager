# Media Provider Plugins

**Entry point group:** `opm.media.provider`
**Template:** `ovos_plugin_manager.templates.media_provider`

`MediaProvider` plugins are the media *catalog/search* layer the OCP pipeline queries
in-process. They replace the old OCP search skills (`OVOSCommonPlaybackSkill` +
`@ocp_search`): instead of broadcasting `ovos.common_play.query` over the bus and waiting
for skills to answer, the pipeline loads providers in-process, gates them by routing, and
calls `search()` directly.

---

## `MediaProvider` base class

```python
from ovos_plugin_manager.templates.media_provider import MediaProvider
```

| Class attribute | Type | Purpose |
|---|---|---|
| `name` | `str` | Stable provider name — registry key and downstream `skill_id`. |
| `media` | `Set[MediaType]` | Media-type gate. Empty ⇒ universal. |
| `playback_type` | `Set[PlaybackType]` | Playback-type gate (`mediavocab.taxonomy.PlaybackType`). Empty ⇒ universal. |
| `genre_filter` | `Set[str]` | Genre-tag gate (`mediavocab.taxonomy.genre`). Empty ⇒ no gate. |

### Abstract methods (must implement)

- `is_available() -> bool` — true if API keys / optional deps / network are present now.
- `search(signals: Signals, lang="en-us") -> List[Release]` — return candidate playables,
  each ranked via `Release.match_confidence` (`0.0`–`1.0`).

### Provided methods

- `matches(signals) -> bool` — default three-axis routing gate (`provider_matches`); only
  override if the `(media, playback_type, genre_filter)` gate is wrong.
- `featured_media(lang="en-us") -> List[Release]` — optional curated/home content.
- `search_safe(signals, lang="en-us")` — `search()` that never raises (returns `[]`),
  used by the pipeline's thread-pool dispatch.
- `shutdown()` — release resources.

---

## Discovery / loading helpers

```python
from ovos_plugin_manager.media_provider import (
    find_media_provider_plugins,   # {name: class}
    load_media_provider_plugin,    # name -> class
    load_media_providers,          # instantiate every enabled+available provider
)
```

Per-provider config lives under `mycroft.conf` → `media_providers` → `<name>`; a provider
is skipped when its config sets `"enabled": false` or when `is_available()` returns false.

---

## Spec conformance

Implements **OVOS-OCP-1**. A `MediaProvider` returns `list[mediavocab.Release]` and is
routed by the same **three-axis** gate (`media` / `playback_type` / `genre_filter`) as
`mediavocab.models.protocols.MetadataProvider`, reusing `provider_matches`. The contract
differs from a metadata *resolver* in one way: a resolver returns a single best identity
match, while media *discovery* returns many candidate playables. Stream extraction is
unchanged — `Release.uri` may be a `"{sei}//{uri}"` deferred stream resolved at playback
by the existing `opm.ocp.extractor` plugins.

> Note: `mediavocab.taxonomy.PlaybackType` (routing axis) is distinct from
> `ovos_utils.ocp.PlaybackType` (backend selector); the two are bridged in the
> pipeline/player, not in the provider.
