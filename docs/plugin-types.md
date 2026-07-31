# Plugin Types & Entry Points

OPM discovers all OVOS plugins through Python package entry points. The `PluginTypes` enum
in `ovos_plugin_manager.utils` maps plugin categories to their canonical entry point group
names. A matching `PluginConfigTypes` enum has the `.config` sub-group names that plugins
use to expose supported-language configuration.

## PluginTypes Enum

### Speech and audio

| Enum value | Entry point group | Template base class |
|---|---|---|
| `STT` | `opm.stt` | `STT` |
| `TTS` | `opm.tts` | `TTS` |
| `WAKEWORD` | `opm.wake_word` | `HotWordEngine` |
| `WAKEWORD_VERIFIER` | `opm.wake_word.verifier` | `HotWordVerifier` |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `VAD` | `opm.VAD` | `VADEngine` |
| `MIC` | `opm.microphone` | `OVOSMicrophone` |

### Hardware, skills, and the pipeline

| Enum value | Entry point group | Template base class |
|---|---|---|
| `PHAL` | `opm.phal` | `PHALPlugin` |
| `ADMIN` | `opm.phal.admin` | `AdminPlugin` |
| `SKILL` | `opm.skill` | N/A |
| `GUI` | `opm.gui` | N/A |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `GUI_ADAPTER` | `opm.gui_adapter` | N/A |
| `PIPELINE` | `opm.pipeline` | `PipelinePlugin` |

### Language and transformers

| Enum value | Entry point group | Template base class |
|---|---|---|
| `TRANSLATE` | `opm.lang.translate` | `LanguageTranslator` |
| `LANG_DETECT` | `opm.lang.detect` | `LanguageDetector` |
| `UTTERANCE_TRANSFORMER` | `opm.transformer.text` | `UtteranceTransformer` |
| `METADATA_TRANSFORMER` | `opm.transformer.metadata` | `MetadataTransformer` |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `AUDIO_TRANSFORMER` | `opm.transformer.audio` | `AudioTransformer` |
| `DIALOG_TRANSFORMER` | `opm.transformer.dialog` | `DialogTransformer` |
| `TTS_TRANSFORMER` | `opm.transformer.tts` | `TTSTransformer` |
| `INTENT_TRANSFORMER` | `opm.transformer.intent` | `IntentTransformer` |

### Phonemes, voice, and text processing

| Enum value | Entry point group | Template base class |
|---|---|---|
| `PHONEME` | `opm.g2p` | `Grapheme2PhonemePlugin` |
| `AUDIO2IPA` | `opm.audio2ipa` | `Audio2IPAPlugin` |
| `VOICE_CLONE` | `opm.vc` | `VoiceClonePlugin` |
| `KEYWORD_EXTRACTION` | `opm.keywords` | `KeywordExtractor` |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `UTTERANCE_SEGMENTATION` | `opm.segmentation` | `UtteranceSegmenter` |
| `TOKENIZATION` | `opm.tokenization` | `Tokenizer` |
| `POSTAG` | `opm.postag` | `PosTagger` |

### Embeddings and knowledge

| Enum value | Entry point group | Template base class |
|---|---|---|
| `EMBEDDINGS` | `opm.embeddings` | N/A |
| `TEXT_EMBEDDINGS` | `opm.embeddings.text` | N/A |
| `VOICE_EMBEDDINGS` | `opm.embeddings.voice` | N/A |
| `IMAGE_EMBEDDINGS` | `opm.embeddings.image` | N/A |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `FACE_EMBEDDINGS` | `opm.embeddings.face` | N/A |
| `TRIPLES` | `opm.triples` | N/A |

### Media

| Enum value | Entry point group | Template base class |
|---|---|---|
| `STREAM_EXTRACTOR` | `opm.ocp.extractor` | N/A |
| `MEDIA_PROVIDER` | `opm.media.provider` | `MediaProvider` |
| `AUDIO_PLAYER` | `opm.media.audio` | N/A |
| `VIDEO_PLAYER` | `opm.media.video` | N/A |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `WEB_PLAYER` | `opm.media.web` | N/A |

### Agents

| Enum value | Entry point group | Template base class |
|---|---|---|
| `PERSONA` | `opm.plugin.persona` | N/A |
| `AGENT_MEMORY` | `opm.agents.memory` | `AgentContextManager` |
| `AGENT_CHAT` | `opm.agents.chat` | `ChatEngine` |
| `AGENT_CHAT_MULTIMODAL` | `opm.agents.chat.multimodal` | N/A |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `AGENT_RETRIEVAL` | `opm.agents.retrieval` | `RetrievalEngine` |
| `AGENT_DOC_RETRIEVAL` | `opm.agents.retrieval.documents` | `DocumentIndexerEngine` |
| `AGENT_QA_RETRIEVAL` | `opm.agents.retrieval.qa` | `QAIndexerEngine` |
| `AGENT_RERANKER` | `opm.agents.reranker` | `ReRankerEngine` |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `AGENT_SUMMARIZER` | `opm.agents.summarizer` | `SummarizerEngine` |
| `AGENT_CHAT_SUMMARIZER` | `opm.agents.summarizer.chat` | N/A |
| `AGENT_EXTRACTIVE_QA` | `opm.agents.extractive_qa` | `ExtractiveQAEngine` |
| `AGENT_NLI` | `opm.agents.nli` | `NaturalLanguageInferenceEngine` |

| Enum value | Entry point group | Template base class |
|---|---|---|
| `AGENT_COREF` | `opm.agents.coref` | N/A |
| `AGENT_YES_NO` | `opm.agents.yesno` | N/A |
| `AGENT_MULTIMODAL_ADAPTER` | `opm.agents.multimodal_adapter` | N/A |
| `AGENT_TOOLBOX` | `opm.agents.toolbox` | `ToolBox` |

### Deprecated solver types

The `AGENT_*` types above replace these. They will be removed in the next major release.

| Enum value | Entry point group |
|---|---|
| `QUESTION_SOLVER` | `opm.solver.question` |
| `CHAT_SOLVER` | `opm.solver.chat` |
| `TLDR_SOLVER` | `opm.solver.summarization` |
| `ENTAILMENT_SOLVER` | `opm.solver.entailment` |

| Enum value | Entry point group |
|---|---|
| `MULTIPLE_CHOICE_SOLVER` | `opm.solver.multiple_choice` |
| `READING_COMPREHENSION_SOLVER` | `opm.solver.reading_comprehension` |
| `COREFERENCE_SOLVER` | `opm.coreference` |

## Legacy / Deprecated Entry Points

OPM still recognizes these old entry point names and maps them internally to their
canonical equivalents. Do not use them in new plugins.

| Old name | Canonical name |
|---|---|
| `mycroft.plugin.stt` | `opm.stt` |
| `mycroft.plugin.tts` | `opm.tts` |
| `mycroft.plugin.wake_word` | `opm.wake_word` |
| `ovos.plugin.phal` | `opm.phal` |

| Old name | Canonical name |
|---|---|
| `ovos.plugin.phal.admin` | `opm.phal.admin` |
| `ovos.plugin.VAD` | `opm.vad` |
| `ovos.plugin.microphone` | `opm.microphone` |
| `ovos.plugin.skill` | `opm.skill` |

| Old name | Canonical name |
|---|---|
| `ovos.plugin.gui` | `opm.gui` |
| `ovos.plugin.g2p` | `opm.g2p` |
| `ovos.plugin.audio2ipa` | `opm.audio2ipa` |
| `neon.plugin.lang.translate` | `opm.lang.translate` |

| Old name | Canonical name |
|---|---|
| `neon.plugin.lang.detect` | `opm.lang.detect` |
| `neon.plugin.text` | `opm.transformer.text` |
| `neon.plugin.metadata` | `opm.transformer.metadata` |
| `neon.plugin.audio` | `opm.transformer.audio` |

| Old name | Canonical name |
|---|---|
| `neon.plugin.solver` | `opm.solver.question` |
| `intentbox.coreference` | `opm.coreference` |
| `intentbox.keywords` | `opm.keywords` |
| `intentbox.segmentation` | `opm.segmentation` |

| Old name | Canonical name |
|---|---|
| `intentbox.tokenization` | `opm.tokenization` |
| `intentbox.postag` | `opm.postag` |
| `ovos.ocp.extractor` | `opm.ocp.extractor` |

---

[← Installation](installation.md) · [Home](index.md) · [Writing a Plugin →](writing-plugins.md)
