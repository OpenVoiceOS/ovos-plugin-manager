# Agent Tool Plugins

**Entry point:** `opm.agents.toolbox`

Tool plugins extend personas with executable functions. A `ToolBox` groups related tools, handles bus-based discovery, and validates inputs/outputs via Pydantic.

---

## Core Classes

### `AgentTool` — `ovos_plugin_manager/templates/agent_tools.py`

A dataclass defining a single executable function and its contract.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Unique snake_case identifier used by agents/LLMs to reference the tool. |
| `description` | `str` | Natural language description; essential for LLM reasoning. |
| `argument_schema` | `Type[ToolArguments]` | Pydantic model defining required input structure. |
| `output_schema` | `Type[ToolOutput]` | Pydantic model defining guaranteed output structure. |
| `tool_call` | `Callable[[ToolArguments], ToolCallReturn]` | Function that executes the tool logic. |

### `ToolArguments` / `ToolOutput`

Base Pydantic models for tool contracts. Subclass these when defining a tool. JSON Schema is generated automatically via `model_json_schema()` for LLM consumption.

### `ToolBox` (ABC) — `ovos_plugin_manager/templates/agent_tools.py`

Abstract base class for tool plugins. Groups related `AgentTool` instances, registers messagebus handlers, and enforces validation.

**Abstract method — must implement:**

```python
def discover_tools(self) -> List[AgentTool]
```

Returns the list of tools provided by this plugin. Called at init and on `refresh_tools()`. Must be idempotent.

**Key methods:**

| Method | Description |
|---|---|
| `bind(bus)` | Attach to messagebus; registers discovery and call handlers. |
| `call_tool(name, tool_kwargs)` | Execute a tool by name with full input/output validation. |
| `get_tool(name)` | Retrieve an `AgentTool` by name; triggers lazy refresh if not cached. |
| `refresh_tools()` | Re-run `discover_tools()` and update the internal cache. |

**Property:**

```python
@property
def tool_json_list(self) -> List[Dict]
```

Returns all tools serialized with JSON Schema argument/output schemas — suitable for sending to an LLM's `tools` API parameter.

**OpenAI tools spec:**

```python
@staticmethod
def tools_to_openai_spec(tool_json_list: List[Dict]) -> List[Dict]   # neutral converter

@property
def openai_tools(self) -> List[Dict]                                  # == tools_to_openai_spec(self.tool_json_list)
```

`tools_to_openai_spec` converts `tool_json_list` entries into the OpenAI
`tools`/function-calling shape (`{"type": "function", "function": {"name",
"description", "parameters"}}`, where `parameters` is the tool's
`argument_schema`). This is the de-facto interchange format across providers
(OpenAI, Ollama, llama.cpp, vLLM, …); each `ChatEngine` re-maps from it to its own
provider format. It is a `@staticmethod` so callers can convert schemas merged from
several toolboxes (as the `ovos-agentic-loop` `NativeToolCallEngine` does); use the
`openai_tools` property for a single toolbox.

---

## Messagebus Interface

Tools expose themselves on the bus automatically when `bind(bus)` is called.

| Message | Direction | Description |
|---|---|---|
| `ovos.persona.tools.discover` | → ToolBox | Broadcast discovery request. |
| `ovos.persona.tools.discover` (response) | ← ToolBox | Returns `{"tools": [...], "toolbox_id": "..."}`. |
| `ovos.persona.tools.<toolbox_id>.call` | → ToolBox | Call a specific tool with `{"name": "...", "kwargs": {...}}`. |
| `ovos.persona.tools.<toolbox_id>.call` (response) | ← ToolBox | Returns `{"result": {...}}` or `{"error": "..."}`. |

This allows agent plugins in separate processes (e.g. MCP or UTCP servers) to discover and call tools dynamically without importing the plugin directly.

---

## Plugin Registration

Register your `ToolBox` subclass in `pyproject.toml`:

```toml
[project.entry-points."opm.agents.toolbox"]
my_toolbox = "my_package:MyToolBox"
```

---

## Writing a ToolBox Plugin

```python
from ovos_plugin_manager.templates.agent_tools import AgentTool, ToolArguments, ToolBox, ToolOutput
from pydantic import Field
from typing import List


class WeatherArgs(ToolArguments):
    location: str = Field(..., description="City name or coordinates.")


class WeatherOutput(ToolOutput):
    temperature_c: float
    condition: str


def fetch_weather(args: WeatherArgs) -> WeatherOutput:
    # ... call weather API ...
    return WeatherOutput(temperature_c=21.5, condition="Sunny")


class WeatherToolBox(ToolBox):
    def __init__(self, bus=None):
        super().__init__(toolbox_id="weather_tools", bus=bus)

    def discover_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_weather",
                description="Get the current weather for a location.",
                argument_schema=WeatherArgs,
                output_schema=WeatherOutput,
                tool_call=fetch_weather,
            )
        ]
```

---

## Validation Behaviour

`call_tool()` enforces a strict lifecycle:

1. **Input** — if `tool_kwargs` is a `dict`, validated against `argument_schema` via Pydantic. If already a `ToolArguments` instance, type-checked against the declared schema.
2. **Execution** — `tool.tool_call(validated_args)` is called.
3. **Output** — if the result is a `dict`, validated against `output_schema`. If already a `ToolOutput` instance, type-checked.

On failure: `ValueError` for input problems, `RuntimeError` for execution or output problems.

Errors from `discover_tools()` at init are logged at `DEBUG` level and retried lazily on first `get_tool()` call. This supports dynamic discovery plugins (MCP, UTCP) where tools may not be available at startup.

---

## Discovery

```python
from ovos_plugin_manager.persona import find_toolbox_plugins

plugins = find_toolbox_plugins()
# {"my_toolbox": MyToolBox, ...}
```
