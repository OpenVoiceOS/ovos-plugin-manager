# Plugin Types & Entry Points

All OVOS plugins are discovered via Python package entry points. The `PluginTypes` enum
in `ovos_plugin_manager.utils` maps plugin categories to their canonical entry point group
names. A matching `PluginConfigTypes` enum provides `.config` sub-group names used when
plugins expose supported-language configuration.

## PluginTypes Enum

| Enum value | Entry point group | Template base class |
|---|---|---|
| `STT` | `opm.stt` | `STT` |
| `TTS` | `opm.tts` | `TTS` |
| `WAKEWORD` | `opm.wake_word` | `HotWordEngine` |
| `WAKEWORD_VERIFIER` | `opm.wake_word.verifier` | `HotWordVerifier` |
| `VAD` | `opm.VAD` | `VADEngine` |
| `MIC` | `opm.microphone` | `OVOSMicrophone` |
| `PHAL` | `opm.phal` | `PHALPlugin` |
| `ADMIN` | `opm.phal.admin` | `AdminPlugin` |
| `SKILL` | `opm.skill` | — |
| `GUI` | `opm.gui` | — |
| `GUI_ADAPTER` | `opm.gui_adapter` | — |
| `PIPELINE` | `opm.pipeline` | `PipelinePlugin` |
| `TRANSLATE` | `opm.lang.translate` | `LanguageTranslator` |
| `LANG_DETECT` | `opm.lang.detect` | `LanguageDetector` |
| `UTTERANCE_TRANSFORMER` | `opm.transformer.text` | `UtteranceTransformer` |
| `METADATA_TRANSFORMER` | `opm.transformer.metadata` | `MetadataTransformer` |
| `AUDIO_TRANSFORMER` | `opm.transformer.audio` | `AudioTransformer` |
| `DIALOG_TRANSFORMER` | `opm.transformer.dialog` | `DialogTransformer` |
| `TTS_TRANSFORMER` | `opm.transformer.tts` | `TTSTransformer` |
| `INTENT_TRANSFORMER` | `opm.transformer.intent` | `IntentTransformer` |
| `PHONEME` | `opm.g2p` | `Grapheme2PhonemePlugin` |
| `AUDIO2IPA` | `opm.audio2ipa` | `Audio2IPAPlugin` |
| `VOICE_CLONE` | `opm.vc` | `VoiceClonePlugin` |
| `KEYWORD_EXTRACTION` | `opm.keywords` | `KeywordExtractor` |
| `UTTERANCE_SEGMENTATION` | `opm.segmentation` | `UtteranceSegmenter` |
| `TOKENIZATION` | `opm.tokenization` | `Tokenizer` |
| `POSTAG` | `opm.postag` | `PosTagger` |
| `EMBEDDINGS` | `opm.embeddings` | — |
| `TEXT_EMBEDDINGS` | `opm.embeddings.text` | — |
| `VOICE_EMBEDDINGS` | `opm.embeddings.voice` | — |
| `IMAGE_EMBEDDINGS` | `opm.embeddings.image` | — |
| `FACE_EMBEDDINGS` | `opm.embeddings.face` | — |
| `TRIPLES` | `opm.triples` | — |
| `STREAM_EXTRACTOR` | `opm.ocp.extractor` | — |
| `AUDIO_PLAYER` | `opm.media.audio` | — |
| `VIDEO_PLAYER` | `opm.media.video` | — |
| `WEB_PLAYER` | `opm.media.web` | — |
| `PERSONA` | `opm.plugin.persona` | — |
| `AGENT_MEMORY` | `opm.agents.memory` | `AgentContextManager` |
| `AGENT_CHAT` | `opm.agents.chat` | `ChatEngine` |
| `AGENT_CHAT_MULTIMODAL` | `opm.agents.chat.multimodal` | — |
| `AGENT_RETRIEVAL` | `opm.agents.retrieval` | `RetrievalEngine` |
| `AGENT_DOC_RETRIEVAL` | `opm.agents.retrieval.documents` | `DocumentIndexerEngine` |
| `AGENT_QA_RETRIEVAL` | `opm.agents.retrieval.qa` | `QAIndexerEngine` |
| `AGENT_RERANKER` | `opm.agents.reranker` | `ReRankerEngine` |
| `AGENT_SUMMARIZER` | `opm.agents.summarizer` | `SummarizerEngine` |
| `AGENT_CHAT_SUMMARIZER` | `opm.agents.summarizer.chat` | — |
| `AGENT_EXTRACTIVE_QA` | `opm.agents.extractive_qa` | `ExtractiveQAEngine` |
| `AGENT_NLI` | `opm.agents.nli` | `NaturalLanguageInferenceEngine` |
| `AGENT_COREF` | `opm.agents.coref` | — |
| `AGENT_YES_NO` | `opm.agents.yesno` | — |
| `AGENT_MULTIMODAL_ADAPTER` | `opm.agents.multimodal_adapter` | — |
| `AGENT_TOOLBOX` | `opm.agents.toolbox` | `ToolBox` |

### Deprecated Solver Types

These are superseded by the `AGENT_*` types above and will be removed in the next major release.

| Enum value | Entry point group |
|---|---|
| `QUESTION_SOLVER` | `opm.solver.question` |
| `CHAT_SOLVER` | `opm.solver.chat` |
| `TLDR_SOLVER` | `opm.solver.summarization` |
| `ENTAILMENT_SOLVER` | `opm.solver.entailment` |
| `MULTIPLE_CHOICE_SOLVER` | `opm.solver.multiple_choice` |
| `READING_COMPREHENSION_SOLVER` | `opm.solver.reading_comprehension` |
| `COREFERENCE_SOLVER` | `opm.coreference` |

## Legacy / Deprecated Entry Points

These old entry point names are still recognized by OPM (mapped internally to their
canonical equivalents) but should not be used in new plugins.

| Old name | Canonical name |
|---|---|
| `mycroft.plugin.stt` | `opm.stt` |
| `mycroft.plugin.tts` | `opm.tts` |
| `mycroft.plugin.wake_word` | `opm.wake_word` |
| `ovos.plugin.phal` | `opm.phal` |
| `ovos.plugin.phal.admin` | `opm.phal.admin` |
| `ovos.plugin.VAD` | `opm.vad` |
| `ovos.plugin.microphone` | `opm.microphone` |
| `ovos.plugin.skill` | `opm.skill` |
| `ovos.plugin.gui` | `opm.gui` |
| `ovos.plugin.g2p` | `opm.g2p` |
| `ovos.plugin.audio2ipa` | `opm.audio2ipa` |
| `neon.plugin.lang.translate` | `opm.lang.translate` |
| `neon.plugin.lang.detect` | `opm.lang.detect` |
| `neon.plugin.text` | `opm.transformer.text` |
| `neon.plugin.metadata` | `opm.transformer.metadata` |
| `neon.plugin.audio` | `opm.transformer.audio` |
| `neon.plugin.solver` | `opm.solver.question` |
| `intentbox.coreference` | `opm.coreference` |
| `intentbox.keywords` | `opm.keywords` |
| `intentbox.segmentation` | `opm.segmentation` |
| `intentbox.tokenization` | `opm.tokenization` |
| `intentbox.postag` | `opm.postag` |
| `ovos.ocp.extractor` | `opm.ocp.extractor` |
