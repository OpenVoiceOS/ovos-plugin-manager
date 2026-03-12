
# FAQ — `ovos-plugin-manager`

## What is `ovos-plugin-manager`?
`ovos-plugin-manager` is OpenVoiceOS plugin manager.

## How do I install it?
```bash
pip install ovos-plugin-manager
```

## What is the current test coverage?
As of 2026-03-11 the test suite achieves **86% line coverage** (1020 tests, 0 failures). Run with:
```bash
uv run pytest test/ --cov=ovos_plugin_manager --cov-report=term-missing
```

## What test files cover the plugin templates?
- `test/unittests/test_embeddings_templates.py` — `EmbeddingsDB`, `TextEmbedder`, `ImageEmbedder`, `FaceEmbedder`, `VoiceEmbedder` and all 30+ distance metrics (`EmbeddingsDB.distance` — `ovos_plugin_manager/templates/embeddings.py:211`)
- `test/unittests/test_media_templates.py` — `MediaBackend`, `AudioPlayerBackend`, `VideoPlayerBackend`, `WebPlayerBackend` and remote variants (`ovos_plugin_manager/templates/media.py`)
- `test/unittests/test_phal_template_extended.py` — `PHALPlugin` mouth events, all stub handlers, shutdown, `runtime_requirements` (`ovos_plugin_manager/templates/phal.py`)
- `test/unittests/test_tts_template_streaming.py` — `ConcatTTS`, `StreamingTTS`, `StreamingTTSCallbacks`, `TTS.plugin_id`, `TTS._init_playback`, `TTS.viseme` (`ovos_plugin_manager/templates/tts.py`)
- `test/unittests/test_thirdparty_sr.py` — `srAudioData.get_flac_data`, `srAudioFile` context manager, `AudioFileStream.read` (`ovos_plugin_manager/thirdparty/sr.py`)
Or for development:
```bash
uv pip install -e ovos-plugin-manager/
```

## Where do I report bugs?
Open an issue on the GitHub repository. Ensure you are targeting the `dev` branch for fixes.

## How do I run tests?
```bash
uv run pytest ovos-plugin-manager/test/ --cov=ovos_plugin_manager
```

## How do I contribute?
1. Fork the repository and create a feature branch from `dev`.
2. Write tests for your changes.
3. Open a PR targeting the `dev` branch.
4. Ensure CI passes before requesting review.

## What Python versions are supported?
See `QUICK_FACTS.md` — currently `>=3.9`.
