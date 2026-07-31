# OVOS Plugin Manager

`ovos-plugin-manager` (OPM) is the plugin discovery, loading, and configuration framework for the OpenVoiceOS ecosystem. It defines the base classes that OVOS plugins implement, and it finds and loads installed plugins at runtime through Python entry points.

![OPM architecture diagram](https://github.com/OpenVoiceOS/ovos-plugin-manager/assets/33701864/8c939267-42fc-4377-bcdb-f7df65e73252)

## Install

```bash
pip install ovos-plugin-manager
```

Media provider plugins need an extra dependency. Install it with:

```bash
pip install ovos-plugin-manager[media]
```

## Usage

Find and load an installed STT plugin by its entry point name.

```python
from ovos_plugin_manager.stt import find_stt_plugins, load_stt_plugin

plugins = find_stt_plugins()
# {'ovos-stt-plugin-whisper': <class 'WhisperSTT'>, ...}

MySTT = load_stt_plugin("ovos-stt-plugin-whisper")
stt = MySTT(config={"lang": "en-US"})
```

Or create a plugin from the active configuration (`mycroft.conf` / `ovos.conf`).

```python
from ovos_plugin_manager.stt import OVOSSTTFactory

stt = OVOSSTTFactory.create()
```

See [docs/index.md](docs/index.md) for the full guide, including TTS, wake word, VAD, and transformer plugins, and how to write a new plugin.

## Related projects

- [OpenVoiceOS/ovos-core](https://github.com/OpenVoiceOS/ovos-core): the OVOS voice assistant core, the main consumer of OPM
- [OpenVoiceOS/ovos-audio](https://github.com/OpenVoiceOS/ovos-audio): loads TTS and audio playback plugins through OPM
- [OpenVoiceOS/ovos-dinkum-listener](https://github.com/OpenVoiceOS/ovos-dinkum-listener): loads STT, wake word, and VAD plugins through OPM
- [OpenVoiceOS/ovos-technical-manual](https://openvoiceos.github.io/ovos-technical-manual/OPM): the OVOS technical manual entry for OPM

## License

Apache License 2.0. See [LICENSE](LICENSE).
