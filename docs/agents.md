# Agent Plugins

The agent plugin system extends OPM with composable NLP components for conversational AI, tool use, and text understanding. Plugins are discovered via Python entry points exactly like all other OPM plugin types.

Base classes: `ovos_plugin_manager/templates/agents.py`, `ovos_plugin_manager/templates/agent_tools.py`

---

## Entry Point Groups

| Group | Base Class | Purpose |
|---|---|---|
| `opm.agents.chat` | `ChatEngine` | Multi-turn chat / agentic loops — `continue_chat(messages)` → `AgentMessage` |
| `opm.agents.chat.multimodal` | `MultimodalChatEngine` | Chat with image/audio/file inputs |
| `opm.agents.toolbox` | `ToolBox` | Groups of callable `AgentTool` functions exposed to agents via bus or direct call |
| `opm.agents.summarizer` | `SummarizerEngine` / `ChatSummarizerEngine` | Document or chat-history summarisation |
| `opm.agents.retrieval` | `RetrievalEngine` | Knowledge-base / vector-index query (`query(q, lang, k)` → `List[Tuple[str, float]]`) |
| `opm.plugin.persona` | `dict` | Static persona config dict; consumed by `ovos-persona` to wire a ChatEngine with a system prompt |

`AgentContextManager` (`agents.py:35`) — optional companion base class for plugins that augment conversation context (RAG, memory, history trimming). Not a standalone entry point group; used inside `ChatEngine` implementations.

---

## Available ToolBoxes (`opm.agents.toolbox`)

Each `ToolBox` implements `discover_tools() → List[AgentTool]` (`agent_tools.py:314`). Tools are callable directly via `ToolBox.call_tool(name, kwargs)` or over the OVOS bus via the `ovos.persona.tools.{toolbox_id}.call` message topic (`agent_tools.py:102`).

| Plugin ID | Class | Tools | Package | API Key |
|---|---|---|---|---|
| `ovos-wikipedia-tools` | `WikipediaToolBox` | `search_wikipedia`, `get_wikipedia_sections`, `get_wikipedia_page` | `ovos-wikipedia-solver` | None — public Wikipedia REST API |
| `ovos-ddg-tools` | `DuckDuckGoToolBox` | `search_duckduckgo`, `get_duckduckgo_infobox` | `ovos-ddg-solver-plugin` | None — DuckDuckGo Instant Answer API |
| `ovos-wolfram-alpha-tools` | `WolframAlphaToolBox` | `compute`, `compute_full` | `ovos-wolfram-alpha-solver` | Optional — free key at developer.wolframalpha.com; demo key bundled |
| `ovos-weather-tools` | `WeatherToolBox` | `get_current_weather`, `get_daily_forecast`, `get_hourly_forecast` | `ovos-skill-weather` | None — Open-Meteo public API |
| `ovos-datetime-tools` | `DateTimeToolBox` | `get_current_datetime`, `convert_timezone`, `get_timezone_for_location` | `ovos-skill-date-time` | None — stdlib + pytz |
| `ovos-ip-tools` | `IPAddressToolBox` | `get_local_ip_addresses`, `get_public_ip` | `ovos-skill-ip` | None |
| `ovos-iss-tools` | `ISSLocationToolBox` | `get_iss_position`, `get_iss_crew` | `ovos-skill-iss-location` | Optional — geonames.org user for reverse geocoding |
| `ovos-speedtest-tools` | `SpeedTestToolBox` | `run_speedtest` | `ovos-skill-speedtest` | None — Speedtest.net |
| `ovos-wallpapers-tools` | `WallpapersToolBox` | `search_wallpapers` | `ovos-skill-wallpapers` | None — wallhaven.cc public API |
| `ovos-wikihow-tools` | `WikiHowToolBox` | `search_wikihow`, `get_wikihow_steps` | `ovos-skill-wikihow` | None — pywikihow scraper |
| `ovos-wordnet-tools` | `WordNetToolBox` | `lookup_word`, `define_word` | `ovos-skill-wordnet` | None — local NLTK corpus |
| `ovos-skill-md-toolbox` | `SkillMDToolBox` | dynamic — one tool per installed `SKILL.md` | `ovos-agentic-loop` | Requires a configured `ChatEngine` (brain) |
| `ovos-filesystem-tools` | `FileSystemToolBox` | `read_file`, `write_file`, `list_directory`, `search_in_files`, `find_files` | `ovos-agentic-loop` | None |
| `ovos-shell-tools` | `ShellToolBox` | `run_command` | `ovos-agentic-loop` | None |
| `ovos-web-search-tools` | `WebSearchToolBox` | `web_search` | `ovos-agentic-loop` | None |
| `ovos-clock-tools` | `ClockToolBox` | `get_current_datetime` | `ovos-agentic-loop` | None |

### Tool schema

Each `AgentTool` (`agent_tools.py:40`) carries:
- `name` — snake_case identifier used by the LLM
- `description` — natural-language purpose shown to the LLM
- `argument_schema` — Pydantic `ToolArguments` subclass; JSON Schema auto-generated for LLM tool-calling APIs
- `output_schema` — Pydantic `ToolOutput` subclass; validated on every call
- `tool_call` — the Python callable; receives an instantiated `ToolArguments`, returns `ToolOutput`

`ToolBox.tool_json_list` (`agent_tools.py:290`) converts all tools to the JSON Schema list format expected by OpenAI / Anthropic / Gemini tool-calling endpoints.

---

## Available Chat Engines (`opm.agents.chat`)

| Plugin ID | Class | Backend | Package |
|---|---|---|---|
| `ovos-chat-openai-plugin` | `OpenAIChatEngine` | OpenAI API | `ovos-openai-plugin` |
| `ovos-chat-gemini-plugin` | `GeminiChatEngine` | Google Gemini | `ovos-gemini-plugin` |
| `ovos-chat-gemini-code-plugin` | `GeminiCodeChatEngine` | Gemini (code) | `ovos-gemini-plugin` |
| `ovos-chat-gemini-session-plugin` | `GeminiSessionChatEngine` | Gemini (session) | `ovos-gemini-plugin` |
| `ovos-chat-claude-plugin` | `ClaudeChatEngine` | Anthropic Claude | `ovos-claude-plugin` |
| `ovos-chat-claude-code-plugin` | `ClaudeCodeChatEngine` | Claude (code) | `ovos-claude-plugin` |
| `ovos-chat-claude-code-session-plugin` | `ClaudeCodeSessionChatEngine` | Claude (session) | `ovos-claude-plugin` |
| `ovos-chat-kilo-plugin` | `KiloChatEngine` | Kilo (Anthropic) | `ovos-kilo-plugin` |
| `ovos-chat-kilo-session-plugin` | `KiloSessionChatEngine` | Kilo (session) | `ovos-kilo-plugin` |
| `ovos-chat-gguf-plugin` | `GGUFChatEngine` | Local GGUF (llama.cpp) | `ovos-gguf-plugin` |
| `ovos-chat-qwen-code-plugin` | `QwenCodeChatEngine` | Qwen-Code | `ovos-qwen-code-plugin` |
| `ovos-chat-opencode-plugin` | `OpenCodeChatEngine` | OpenCode | `ovos-opencode-plugin` |
| `ovos-chat-opencode-session-plugin` | `OpenCodeSessionChatEngine` | OpenCode (session) | `ovos-opencode-plugin` |
| `ovos-wikigpt` | `WikiGPTSolver` | Wikipedia RAG | `ovos-wikipedia-solver` |
| `ovos-react-loop` | `ReActLoopEnginePlugin` | ReAct over any ChatEngine + ToolBoxes | `ovos-agentic-loop` |
| `ovos-plan-execute-loop` | `PlanAndExecuteEnginePlugin` | Plan-and-Execute | `ovos-agentic-loop` |
| `ovos-reflexion-loop` | `ReflexionEnginePlugin` | Reflexion | `ovos-agentic-loop` |
| `ovos-self-ask-loop` | `SelfAskEnginePlugin` | Self-Ask | `ovos-agentic-loop` |
| `ovos-chain-of-thought-loop` | `ChainOfThoughtEnginePlugin` | Chain-of-Thought | `ovos-agentic-loop` |
| `ovos-mos-king-reranker` | `ReRankerKingMoSPlugin` | Mixture-of-Solvers (reranker) | `ovos-MoS` |
| `ovos-mos-king-generative` | `GenerativeKingMoSPlugin` | MoS (generative king) | `ovos-MoS` |
| `ovos-mos-democracy` | `DemocracyMoSPlugin` | MoS (majority vote) | `ovos-MoS` |
| `ovos-mos-duopoly-reranker` | `ReRankerDuopolyMoSPlugin` | MoS (duopoly reranker) | `ovos-MoS` |
| `ovos-mos-duopoly-generative` | `GenerativeDuopolyMoSPlugin` | MoS (duopoly generative) | `ovos-MoS` |

### Multimodal Chat Engines (`opm.agents.chat.multimodal`)

| Plugin ID | Class | Backend | Package |
|---|---|---|---|
| `ovos-chat-multimodal-gemini-plugin` | `GeminiMultimodalChatEngine` | Gemini | `ovos-gemini-plugin` |
| `ovos-chat-multimodal-claude-plugin` | `ClaudeMultimodalChatEngine` | Claude | `ovos-claude-plugin` |
| `ovos-chat-multimodal-kilo-plugin` | `KiloMultimodalChatEngine` | Kilo | `ovos-kilo-plugin` |
| `ovos-chat-multimodal-qwen-code-plugin` | `QwenCodeMultimodalChatEngine` | Qwen-Code | `ovos-qwen-code-plugin` |

`ChatEngine.continue_chat` signature:
```python
def continue_chat(self, messages: List[AgentMessage],
                  session_id: str = "default",
                  lang: Optional[str] = None,
                  units: Optional[str] = None,
                  tools: Optional[List[Dict[str, Any]]] = None) -> AgentMessage:
```

`ChatEngine` also provides `stream_tokens`, `stream_sentences`, and `get_response` helpers. Plugins only need to implement `continue_chat`.

### Tool calling

A conversation can carry tool turns. `MessageRole.TOOL` is the role of a tool
result, and `AgentMessage` carries optional tool fields:

- `tool_calls: Optional[List[ToolCall]]` — set on an `ASSISTANT` message that
  requests tool invocations (`ToolCall(id, name, arguments)`); `content` may be `""`.
- `tool_call_id` / `name` — set on a `TOOL` message, identifying the `ToolCall` it
  answers.

`continue_chat` accepts an optional `tools` argument (OpenAI `tools` spec — see
[`agent-tools.md`](agent-tools.md)). An engine that can use it sets the class
attribute `supports_tools = True` and returns an assistant `AgentMessage` whose
`tool_calls` are populated when the model requests them. Engines that don't support
tools leave `supports_tools = False` and ignore the argument — the new kwarg is
optional, so pre-existing 4-arg `continue_chat` overrides keep working unchanged.
The ordering invariant providers expect: an assistant message carrying `tool_calls`
must be followed by one `TOOL` message per `ToolCall.id`. The orchestration loop
that drives this lives in `ovos-agentic-loop` (`NativeToolCallEngine`), not in the
provider engines.

---

## Available Personas (`opm.plugin.persona`)

Each persona entry is a dict defining `chat_engine`, `system_prompt`, and optionally `toolboxes`. Loaded and wired by the `ovos-persona` service.

| Persona ID | Backend | Package |
|---|---|---|
| `OpenAI` | `ovos-chat-openai-plugin` | `ovos-openai-plugin` |
| `Claude` | `ovos-chat-claude-plugin` | `ovos-claude-plugin` |
| `Gemini` | `ovos-chat-gemini-plugin` | `ovos-gemini-plugin` |
| `Kilo` | `ovos-chat-kilo-plugin` | `ovos-kilo-plugin` |
| `QwenCode` | `ovos-chat-qwen-code-plugin` | `ovos-qwen-code-plugin` |
| `OpenCode` | `ovos-chat-opencode-plugin` | `ovos-opencode-plugin` |
| `Wikipedia` | Wikipedia solver | `ovos-wikipedia-solver` |
| `WikiGPT` | `ovos-wikigpt` | `ovos-wikipedia-solver` |
| `DuckDuckGo` | DDG solver | `ovos-ddg-solver-plugin` |
| `Wolfram Alpha` | Wolfram solver | `ovos-wolfram-alpha-solver` |
| `WikiHow` | WikiHow solver | `ovos-skill-wikihow` |
| `Wordnet` | WordNet solver | `ovos-skill-wordnet` |

---

## How to Implement a ToolBox

Register under `opm.agents.toolbox` in `pyproject.toml`:

```toml
[project.entry-points."opm.agents.toolbox"]
my-tools = "my_package.toolbox:MyToolBox"
```

Minimal implementation (`agent_tools.py:56`):

```python
from ovos_plugin_manager.templates.agent_tools import AgentTool, ToolArguments, ToolBox, ToolOutput
from pydantic import Field

class MyArgs(ToolArguments):
    query: str = Field(..., description="Input text.")

class MyOutput(ToolOutput):
    result: str = Field(..., description="Tool result.")

class MyToolBox(ToolBox):
    toolbox_id = "my-tools"

    def __init__(self, config=None):
        self.config = config or {}
        super().__init__(toolbox_id=self.toolbox_id)

    def discover_tools(self):
        return [AgentTool(
            name="my_tool",
            description="Does something useful.",
            argument_schema=MyArgs,
            output_schema=MyOutput,
            tool_call=lambda args: MyOutput(result=args.query.upper()),
        )]
```

`ToolBox.call_tool` validates input and output against the Pydantic schemas automatically (`agent_tools.py:195`). `discover_tools` is called once at init and again lazily if a tool is not found in the cache (`agent_tools.py:104`).

---

## How to Implement a ChatEngine

Register under `opm.agents.chat` in `pyproject.toml`:

```toml
[project.entry-points."opm.agents.chat"]
my-chat-engine = "my_package.chat:MyChatEngine"
```

Minimal implementation (`agents.py:195`):

```python
from ovos_plugin_manager.templates.agents import ChatEngine, AgentMessage, MessageRole
from typing import List, Optional

class MyChatEngine(ChatEngine):
    def continue_chat(self, messages: List[AgentMessage],
                      session_id: str = "default",
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> AgentMessage:
        # messages[-1] is the latest user message
        reply = call_my_llm_api([m.__dict__ for m in messages])
        return AgentMessage(role=MessageRole.ASSISTANT, content=reply)
```

For streaming, override `stream_tokens` (token-level) or `stream_sentences` (sentence-level, TTS-ready) (`agents.py:228–278`). The default implementations fall back to `continue_chat`.

---

## Configuration

Config is passed as a plain `dict` to `__init__`. OPM reads plugin config from the OVOS `Configuration()` singleton under the plugin's entry point name. Standard keys used by most agent plugins:

| Key | Type | Default | Description |
|---|---|---|---|
| `lang` | `str` | session lang | BCP-47 language code |
| `system_prompt` | `str` | `""` | System prompt for `AgentContextManager` plugins (`agents.py:61`) |
| `context_ttl` | `int` | `120` | Seconds before coreference context is pruned (`agents.py:598`) |

ToolBox-specific keys are documented in each plugin's module docstring.
