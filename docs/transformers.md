# Transformer Pipelines

Transformers are ordered chains that rewrite an artifact at a fixed point in the voice
pipeline: raw audio before STT, utterances after STT, message context before intent
matching, the selected intent before dispatch, dialog text before TTS, and synthesized
audio before playback.

`ovos_plugin_manager.transformer_services` has the canonical runner services that load,
order, and chain transformer plugins. ovos-core, ovos-audio, ovos-dinkum-listener,
ovos-tts-server, ovos-stt-server, hivemind-core, hivemind-audio-binary-protocol, and the
HiveMind satellites all use these services, so the same plugin works unmodified in each of
them.

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

Loading is config-gated and opt-in. A plugin loads only when its name appears in the
chain's config section. You can disable an entry with `"active": false` without removing
its config.

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

Chains run in ascending priority order (OVOS-TRANSFORM §4): a plugin with `priority = 1`
runs before one with `priority = 50`. The default is 50. A later plugin sees, and may
override, an earlier plugin's output.

A deployer can bypass priorities entirely with an explicit `order` list. A loaded plugin
that is absent from the list does not run:

```json
{
  "utterance_transformers": {
    "order": ["plugin-that-must-run-first", "plugin-that-runs-second"]
  }
}
```

### Cancellation

A transformer can cancel the whole lifecycle (OVOS-TRANSFORM §8.1) by returning both
`"canceled": true` and a `"cancel_reason"` in its context. The runner stamps `cancel_by`
with the emitting plugin's name and stops the chain. The consumer then ends the lifecycle
(for example, ovos-core emits `ovos.utterance.cancelled`, then `ovos.utterance.handled`).
Stop-word plugins such as `ovos-utterance-plugin-cancel` use this mechanism.

### Error handling

A plugin exception never stops the chain. The runner logs the exception and the chain
continues with the previous plugin's output.

## Where chains run — and surprise interactions

The same chain type can run in more than one process. That is by design, but enable each
plugin in exactly one place per deployment. Otherwise its effect applies twice.

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

Moving a chain to a server is a deliberate way to centralize behavior. Enable a dialog
transformer on ovos-tts-server, and every device that synthesizes through it gets the same
tone or persona rewrite. The server then returns audio for different text than the client
sent. This looks surprising from the client, but it is the intended effect. The same
applies to a shared STT server that corrects transcripts for every client, or a HiveMind
server that cancels utterances by policy for the whole mesh.

Guidelines:

- For a per-device effect (denoise for one bad microphone, a voice effect on one speaker),
  enable the plugin on the device or satellite.
- For a fleet-wide effect (a global persona or tone, shared transcript corrections, policy
  stop-words), enable the plugin on the server everyone uses.
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

All runners accept an optional bus, which they bind to plugins that support it, or you can
bind it later with `set_bus()`. Each runner exposes `plugins` (execution order),
`get_available_plugins()`, `transform(...)`, and `shutdown()`.

---

[← Configuration](configuration.md) · [Home](index.md) · [Voice Cloning →](voice-clone.md)
