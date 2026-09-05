
# Quick Facts — `ovos-plugin-manager`

OpenVoiceOS plugin manager

| Feature | Details |
|---------|---------|
| Package Name | `ovos-plugin-manager` |
| Version | `2.2.3a1` |
| License | Apache-2.0 |
| Repository | [https://github.com/OpenVoiceOS/OVOS-plugin-manager](https://github.com/OpenVoiceOS/OVOS-plugin-manager) |
| Python Support | >=3.9 |

## Agent Plugin Entry Point Groups

| Group | Base Class | Purpose |
|---|---|---|
| `opm.agents.chat` | `ChatEngine` | Multi-turn chat engines and agentic loops |
| `opm.agents.chat.multimodal` | `MultimodalChatEngine` | Chat with image/audio/file inputs |
| `opm.agents.toolbox` | `ToolBox` | Grouped callable `AgentTool` functions |
| `opm.agents.summarizer` | `SummarizerEngine` | Document/chat summarisation |
| `opm.agents.retrieval` | `RetrievalEngine` | Knowledge-base query |
| `opm.plugin.persona` | `dict` | Static persona config wired by `ovos-persona` |

See `docs/agents.md` for the full registry of installed plugins.
