# Transformer Pipelines

Transformers are ordered black-box chains that rewrite an artifact at a
fixed point in the voice pipeline: raw audio before STT, utterances after
STT, message context before intent matching, the selected intent before
dispatch, dialog text before TTS, and synthesized audio before playback.

`ovos_plugin_manager.transformer_services` provides the canonical runner
services that load, order and chain transformer plugins. They are consumed
by ovos-core, ovos-audio, ovos-dinkum-listener, ovos-tts-server,
ovos-stt-server, hivemind-core, hivemind-audio-binary-protocol and the
HiveMind satellites — the same plugin works unmodified in all of them.

## The six chains

| Runner service | Plugin base class | Config section | Runs |
|---|---|---|---|
| `AudioTransformersService` | `AudioTransformer` | `audio_transformers` | on raw audio before STT |
| `UtteranceTransformersService` | `UtteranceTransformer` | `utterance_transformers` | on transcripts before intent matching |
| `MetadataTransformersService` | `MetadataTransformer` | `metadata_transformers` | on message context before intent matching |
| `IntentTransformersService` | `IntentTransformer` | `intent_transformers` | on the selected intent before its handler |
| `DialogTransformersService` | `DialogTransformer` | `dialog_transformers` | on dialog text before TTS |
| `TTSTransformersService` | `TTSTransformer` | `tts_transformers` | on synthesized audio before playback |

## Configuration

Loading is **config-gated and opt-in**: a plugin only loads when its name
appears in the chain's config section, and an entry can be disabled with
`"active": false` without removing its config.

```json
{
  "utterance_transformers": {
    "ovos-utterance-normalizer": {},
    "ovos-utterance-corrections-plugin": {"active": true}
  },
  "dialog_transformers": {
    "ovos-dialog-transformer-openai-plugin": {"rewrite_prompt": "rewrite the text as if you were explaining it to a 5 year old"}
  },
  "tts_transformers": {
    "ovos-tts-transformer-sox-plugin": {"pitch": 300}
  }
}
```

### Ordering

Chains run in **ascending priority order** (OVOS-TRANSFORM §4): a plugin
with `priority = 1` runs before one with `priority = 50`. The default is
50. Later plugins see — and may override — earlier plugins' output.

A deployer can bypass priorities entirely with an explicit `order` list;
loaded plugins absent from the list do not run:

```json
{
  "utterance_transformers": {
    "order": ["plugin-that-must-run-first", "plugin-that-runs-second"]
  }
}
```

### Cancellation

A transformer can cancel the whole lifecycle (OVOS-TRANSFORM §8.1) by
returning both `"canceled": true` and a `"cancel_reason"` in its context.
The runner stamps `cancel_by` with the emitting plugin's name and stops the
chain; the consumer terminates the lifecycle (e.g. ovos-core emits
`ovos.utterance.cancelled` → `ovos.utterance.handled`). This is how
stop-word plugins like `ovos-utterance-plugin-cancel` work.

### Error handling

A plugin exception never aborts the chain: it is logged and the chain
proceeds with the previous plugin's output.

## Where chains run — and surprise interactions

The same chain type can run in more than one process. That is a feature —
but each plugin should be enabled in **exactly one** place per deployment,
or its effect is applied twice.

| Surface | Chains it can run |
|---|---|
| ovos-dinkum-listener | audio |
| ovos-core | utterance, metadata, intent |
| ovos-audio | dialog, tts |
| ovos-stt-server | audio, utterance |
| ovos-tts-server | dialog, tts |
| hivemind-core (text path) | utterance, metadata, dialog |
| hivemind-audio-binary-protocol | audio, utterance, metadata, dialog, tts |
| HiveMind satellites (on device) | audio (pre-send), utterance (relay), tts (pre-playback) |

Moving a chain **to a server is a deliberate centralization tool**: enable a
dialog transformer on ovos-tts-server and every device that synthesizes
through it gets the same tone/persona rewrite globally — the server then
returns audio for *different text than you sent*, which looks surprising
from the client but is exactly the point. The same applies to a shared STT
server correcting transcripts for every client, or a HiveMind server
canceling utterances by policy for the whole mesh.

Rules of thumb:

- **Per-device effects** (denoise for one bad microphone, a voice effect on
  one speaker) → enable on the device/satellite.
- **Fleet-wide effects** (a global persona/tone, shared transcript
  corrections, policy stop-words) → enable on the server everyone uses.
- Never enable the same plugin on both sides of a connection.

## Consuming the runners

```python
from ovos_plugin_manager.transformer_services import UtteranceTransformersService

# config may be the full core configuration (the section is extracted)
# or the section mapping itself — handy for non-mycroft.conf consumers
service = UtteranceTransformersService(bus=bus, config={"my-plugin": {}})
utterances, context = service.transform(["hello world"], {"lang": "en-US"})
service.shutdown()
```

All runners accept an optional bus (bound to plugins that support it, or
later via `set_bus()`) and expose `plugins` (execution order),
`get_available_plugins()`, `transform(...)` and `shutdown()`.
