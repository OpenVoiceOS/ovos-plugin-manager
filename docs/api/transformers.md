# Transformer Plugins

Transformers are lightweight plugins that intercept and optionally modify data at various
stages of the OVOS pipeline. All transformers share a common interface:
`bind(bus)`, `initialize()`, `transform(...)`, `default_shutdown()`.

---

## Audio Transformers

**Entry point group:** `opm.transformer.audio`
**Template:** `ovos_plugin_manager.templates.transformers.AudioTransformer`

Run during the listen stage, receiving raw audio chunks from the microphone before STT.

### Constructor

```python
AudioTransformer(name: str, priority: int = 50, config: Optional[dict] = None)
```

| Attribute | Description |
|---|---|
| `noise_feed` | `ReadWriteStream` — 3-second buffer of non-speech audio. |
| `hotword_feed` | `ReadWriteStream` — 3-second buffer of hotword audio. |
| `speech_feed` | `ReadWriteStream` — 10-second buffer of speech audio. |
| `sample_rate` | Audio sample rate (from `listener` config, default 16000). |
| `sample_width` | Bytes per sample (default 2). |
| `channels` | Number of channels (default 1). |

### Transform stages

| Method | When called | Notes |
|---|---|---|
| `on_audio(chunk)` | For every non-speech chunk | May modify and return chunk. |
| `on_hotword(chunk)` | When a hotword is detected | May prepare for incoming speech. |
| `on_speech(chunk)` | For each chunk during recording | May modify and return chunk. |
| `on_speech_end(chunk)` | Full utterance audio is ready | May modify and return audio. |
| `transform(audio_data)` | After `on_speech_end` | Return `(audio_data, context_dict)`. Additional context is merged into the utterance message. |

### `reset()`

Clear all audio buffers. Called at the end of each prediction cycle.

---

## `AudioLanguageDetector`

**Entry point group:** `opm.transformer.audio` (same as `AudioTransformer`)
**Template:** `ovos_plugin_manager.templates.transformers.AudioLanguageDetector`

Extends `AudioTransformer`. Detects spoken language from audio.

### Abstract method

#### `detect(audio_data: bytes, valid_langs: Optional[List[str]] = None) -> Tuple[str, float]`

Return `(bcp47_lang, confidence)`.

### Provided method

#### `transform(audio_data: bytes) -> Tuple[bytes, dict]`

Calls `detect` and returns the audio unchanged plus context
`{"stt_lang": lang, "lang_probability": prob}`.

---

## Utterance Transformers

**Entry point group:** `opm.transformer.text`
**Template:** `ovos_plugin_manager.templates.transformers.UtteranceTransformer`

Run after STT, before the intent service.

### Constructor

```python
UtteranceTransformer(name: str, priority: int = 50, config: Optional[dict] = None)
```

### Abstract-ish method

#### `transform(utterances: List[str], context: dict = None) -> Tuple[List[str], dict]`

Optionally rewrite utterances and/or return additional context. Default returns inputs
unchanged.

---

## Metadata Transformers

**Entry point group:** `opm.transformer.metadata`
**Template:** `ovos_plugin_manager.templates.transformers.MetadataTransformer`

Run after utterance transformers, before intent matching. Used to inject or normalise
`Message.context`.

### Method

#### `transform(context: dict = None) -> dict`

Return a (possibly modified) context dict.

---

## Intent Transformers

**Entry point group:** `opm.transformer.intent`
**Template:** `ovos_plugin_manager.templates.transformers.IntentTransformer`

Run after intent matching, before the intent handler fires. Can inject data into the
matched intent (e.g. perform NER).

### Abstract method

#### `transform(intent: IntentHandlerMatch) -> IntentHandlerMatch`

Modify or augment the `IntentHandlerMatch` before it is dispatched to the skill.

---

## Dialog Transformers

**Entry point group:** `opm.transformer.dialog`
**Template:** `ovos_plugin_manager.templates.transformers.DialogTransformer`

Run before TTS. Modify the dialog text before it is spoken.

### Method

#### `transform(dialog: str, context: dict = None) -> Tuple[str, dict]`

Return `(modified_dialog, updated_context)`.

---

## TTS Transformers

**Entry point group:** `opm.transformer.tts`
**Template:** `ovos_plugin_manager.templates.transformers.TTSTransformer`

Run after TTS synthesis, before playback. Can post-process the generated WAV file
(e.g. apply audio effects).

### Method

#### `transform(wav_file: str, context: dict = None) -> Tuple[str, dict]`

Return `(path_to_transformed_wav, updated_context)`.

---

## Common interface (all transformers)

| Method | Description |
|---|---|
| `bind(bus=None)` | Attach the OVOS message bus. |
| `initialize()` | Perform any startup actions (subscribe to bus events, load models, etc.). |
| `default_shutdown()` | Release resources and unsubscribe from bus events. |

### Priority

Lower `priority` values run first. Default is `50`.

---

## Configuration

Each transformer type reads config from its own section in `ovos.conf`:

```json
{
  "utterance_transformers": {
    "my-utterance-transformer": {"enabled": true, "some_option": 42}
  },
  "audio_transformers": {
    "my-audio-transformer": {"sample_rate": 16000}
  },
  "dialog_transformers": {
    "my-dialog-transformer": {}
  },
  "metadata_transformers": {
    "my-metadata-transformer": {}
  },
  "intent_transformers": {
    "my-intent-transformer": {}
  }
}
```
