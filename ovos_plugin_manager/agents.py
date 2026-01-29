from typing import Dict, Type

from ovos_plugin_manager.templates.agents import (
    AgentContextManager, MultimodalAdapter, RetrievalEngine, ChatEngine, MultimodalChatEngine, SummarizerEngine,
    ChatSummarizerEngine, ExtractiveQAEngine, ReRankerEngine, YesNoEngine, NaturalLanguageInferenceEngine,
    DocumentIndexerEngine, QAIndexerEngine, CoreferenceEngine)
from ovos_plugin_manager.utils import PluginTypes


def find_memory_plugins() -> Dict[str, Type[AgentContextManager]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_MEMORY)


def load_memory_plugin(module_name: str) -> Type[AgentContextManager]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_MEMORY)


def find_multimodal_adapter_plugins() -> Dict[str, Type[MultimodalAdapter]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_MULTIMODAL_ADAPTER)


def load_multimodal_adapter_plugin(module_name: str) -> Type[MultimodalAdapter]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_MULTIMODAL_ADAPTER)


def find_retrieval_plugins() -> Dict[str, Type[RetrievalEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_RETRIEVAL)


def load_retrieval_plugin(module_name: str) -> Type[RetrievalEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_RETRIEVAL)


def find_chat_plugins() -> Dict[str, Type[ChatEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_CHAT)


def load_chat_plugin(module_name: str) -> Type[ChatEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_CHAT)


def find_multimodal_chat_plugins() -> Dict[str, Type[MultimodalChatEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_CHAT_MULTIMODAL)


def load_multimodal_chat_plugin(module_name: str) -> Type[MultimodalChatEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_CHAT_MULTIMODAL)


def find_summarizer_plugins() -> Dict[str, Type[SummarizerEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_SUMMARIZER)


def load_summarizer_plugin(module_name: str) -> Type[SummarizerEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_SUMMARIZER)


def find_chat_summarizer_plugins() -> Dict[str, Type[ChatSummarizerEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_CHAT_SUMMARIZER)


def load_chat_summarizer_plugin(module_name: str) -> Type[ChatSummarizerEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_CHAT_SUMMARIZER)


def find_extractive_qa_plugins() -> Dict[str, Type[ExtractiveQAEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_EXTRACTIVE_QA)


def load_extractive_qa_plugin(module_name: str) -> Type[ExtractiveQAEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_EXTRACTIVE_QA)


def find_reranker_plugins() -> Dict[str, Type[ReRankerEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_RERANKER)


def load_reranker_plugin(module_name: str) -> Type[ReRankerEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_RERANKER)


def find_yesno_plugins() -> Dict[str, Type[YesNoEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_YES_NO)


def load_yesno_plugin(module_name: str) -> Type[YesNoEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_YES_NO)


def find_natural_language_inference_plugins() -> Dict[str, Type[NaturalLanguageInferenceEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_NLI)


def load_natural_language_inference_plugin(module_name: str) -> Type[NaturalLanguageInferenceEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_NLI)


def find_document_indexer_plugins() -> Dict[str, Type[DocumentIndexerEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_DOC_RETRIEVAL)


def load_document_indexer_plugin(module_name: str) -> Type[DocumentIndexerEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_DOC_RETRIEVAL)


def find_qa_indexer_plugins() -> Dict[str, Type[QAIndexerEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_QA_RETRIEVAL)


def load_qa_indexer_plugin(module_name: str) -> Type[QAIndexerEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_QA_RETRIEVAL)


def find_coreference_plugins() -> Dict[str, Type[CoreferenceEngine]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_COREF)


def load_coreference_plugin(module_name: str) -> Type[CoreferenceEngine]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_COREF)