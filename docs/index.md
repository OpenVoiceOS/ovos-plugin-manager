
# OVOS Plugin Manager (OPM) Documentation

`ovos-plugin-manager` (OPM) is the central plugin discovery, loading, and configuration
framework for the OpenVoiceOS ecosystem. It defines the base classes (templates) that all
OVOS plugins must implement, and provides factory methods and utilities for finding and
loading installed plugins at runtime via Python entry points.

## Contents

- [Plugin Types & Entry Points](plugin-types.md) — full `PluginTypes` enum and `setup.py` entry point names
- [Transformer Pipelines](transformers.md) — the six transformer chains, runner services, config, ordering and deployment surfaces
- [Writing a Plugin](writing-plugins.md) — step-by-step guide with `setup.py` template
- [Configuration Utilities](configuration.md) — `get_plugin_config`, language configs, sorting
- [Installation Utilities](installation.md) — `pip_install`, `search_pip`
- **API References**
  - [STT](api/stt.md) — Speech-to-Text
  - [TTS](api/tts.md) — Text-to-Speech
  - [Wake Word](api/wake-word.md) — Hotword / Wake Word detection
  - [VAD](api/vad.md) — Voice Activity Detection
  - [Microphone](api/microphone.md) — Audio input sources
  - [PHAL](api/phal.md) — Platform/Hardware Abstraction Layer
  - [Transformers](api/transformers.md) — Audio, Utterance, Dialog, Metadata, TTS, Intent transformers
  - [Agents & Solvers](api/agents.md) — NLP solver and agent engine plugins
  - [Agent Tools](api/agent-tools.md) — ToolBox plugin API (`opm.agents.toolbox`)
- [Agent Plugins](agents.md) — all available ChatEngine, ToolBox, and Persona plugins with entry point registry
  - [Pipeline](api/pipeline.md) — Intent matching pipeline plugins
  - [Media Provider](api/media-provider.md) — OCP catalog/search providers (`opm.media.provider`, OVOS-OCP-1)
  - [Language](api/language.md) — Translation and language detection plugins

## Architecture Overview

```
ovos-core / ovos-dinkum-listener / ovos-audio
        │
        └── ovos-plugin-manager
                ├── find_plugins(PluginTypes.STT)   → {name: entrypoint, ...}
                ├── load_plugin(name, PluginTypes.STT) → Class
                └── OVOSSTTFactory.create(config)   → STT instance
```

Plugins are Python packages that register themselves under a well-known entry point group
(e.g. `opm.stt`). OPM calls `importlib.metadata.entry_points()` to discover installed
plugins without any manual registration.

## Quick Start

### Find all installed STT plugins

```python
from ovos_plugin_manager.stt import find_stt_plugins
plugins = find_stt_plugins()
# {'ovos-stt-plugin-whisper': <class 'WhisperSTT'>, ...}
```

### Load a plugin class by entry point name

```python
from ovos_plugin_manager.stt import load_stt_plugin
MySTT = load_stt_plugin("ovos-stt-plugin-whisper")
stt = MySTT(config={"lang": "en-US"})
```

### Create a plugin from configuration

```python
from ovos_plugin_manager.stt import OVOSSTTFactory
# reads stt.module from mycroft.conf / ovos.conf
stt = OVOSSTTFactory.create()
```

### Inspect a plugin (installed or not)

```python
from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin
p = OpenVoiceOSPlugin.from_name("ovos-stt-plugin-whisper")
print(p.human_name)   # "Whisper STT"
print(p.is_installed) # True
print(p.json)         # full metadata dict
```
