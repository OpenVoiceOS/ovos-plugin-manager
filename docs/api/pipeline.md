# Pipeline Plugins

**Entry point group:** `opm.pipeline`
**Template:** `ovos_plugin_manager.templates.pipeline`

Pipeline plugins implement intent-matching stages for `ovos-core`. Each stage is given an
utterance and returns an `IntentHandlerMatch` (or `None`) indicating whether and how the
utterance should be handled.

---

## `IntentHandlerMatch` dataclass

```python
from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
```

| Field | Type | Description |
|---|---|---|
| `match_type` | `str` | Name of the service/handler that matched (e.g. `"padatious:intent"`). |
| `match_data` | `Optional[dict]` | Extracted entities or intent-specific data. |
| `skill_id` | `Optional[str]` | ID of the skill that owns the handler. |
| `utterance` | `Optional[str]` | Original utterance that triggered the match. |
| `updated_session` | `Optional[Session]` | Modified session state (if the plugin changes session). |

---

## `PipelinePlugin` base class

```python
from ovos_plugin_manager.templates.pipeline import PipelinePlugin
```

### Constructor

```python
PipelinePlugin(
    bus: Optional[Union[MessageBusClient, FakeBus]] = None,
    config: Optional[dict] = None,
)
```

### Abstract method (must implement)

#### `match(utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]`

Attempt to match `utterances` against this plugin's knowledge. Return an
`IntentHandlerMatch` on success, `None` otherwise.

---

## `ConfidenceMatcherPipeline` base class

```python
from ovos_plugin_manager.templates.pipeline import ConfidenceMatcherPipeline
```

Extends `PipelinePlugin`. For plugins that score utterances with confidence values
without directly triggering handlers. Used by stages like converse, common-QA, etc.

---

## Configuration

Pipeline plugins are configured under `ovos.conf`:

```json
{
  "intents": {
    "pipeline": [
      "converse",
      "padatious_high",
      "adapt",
      "common_qa",
      "fallback_high",
      "fallback_low"
    ]
  }
}
```

Each name in the list must correspond to a plugin registered under `opm.pipeline`.
