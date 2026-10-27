# Voice Cloning Plugins (`opm.vc`)

Voice-cloning plugins perform audio-to-audio voice conversion. Given a source speech file
and a short reference speaker sample, the plugin outputs new audio that carries the
linguistic content of the source but sounds like the reference speaker.

> **Scope boundary: text input is out of scope.** Voice cloning from text (zero-shot TTS
> with a speaker reference) belongs in TTS plugins, and you configure it through the TTS
> plugin's own `config` section. The `opm.vc` family takes only already-recorded speech as
> input. It never receives raw text.

---

## Contract

Base class: `ovos_plugin_manager.templates.vc.VoiceClonePlugin`

Entry-point group: `opm.vc`  
Config section: `voice_clone`

| Method / Property | Description |
|---|---|
| `clone_voice(audio, reference_voice, out_path=None) → str` | **Only abstract method.** Convert source WAV `audio` to the voice of `reference_voice`. Returns path to a 16-bit output WAV. |
| `sample_rate → int` | Output sample rate in Hz (default 24000). Override to advertise the engine's native rate. |
| `available_languages → List[str]` | BCP-47 tags supported. Return `[]` for language-agnostic engines (default). |

`__init__(self, config=None)` stores the plugin-specific config dict. No other
initialization step is required.

---

## Registering a Plugin

```toml
# pyproject.toml
[project.entry-points."opm.vc"]
my-vc-plugin = "my_package.vc:MyVoiceClonePlugin"
```

```json
// mycroft.conf  (or equivalent OVOS config)
{
  "voice_clone": {
    "module": "my-vc-plugin",
    "my-vc-plugin": {
      "model_path": "/path/to/model.onnx"
    }
  }
}
```

---

## Discovery and Factory API

```python
from ovos_plugin_manager.vc import (
    find_voice_clone_plugins,
    load_voice_clone_plugin,
    OVOSVoiceClonerFactory,
)

# List all installed plugins
plugins = find_voice_clone_plugins()  # dict: name -> class

# Load a specific plugin class (not instantiated)
cls = load_voice_clone_plugin("my-vc-plugin")

# Instantiate from config
cloner = OVOSVoiceClonerFactory.create(config)
out_wav = cloner.clone_voice("/path/source.wav", "/path/reference.wav")
```

---

## Implementations

Implementations register under the `opm.vc` entry-point group. Find them with
`find_voice_clone_plugins()`.

---

[← Transformers](transformers.md) · [Home](index.md) · [Agent Plugins →](agents.md)
