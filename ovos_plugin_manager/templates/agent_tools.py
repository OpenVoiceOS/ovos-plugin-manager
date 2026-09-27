# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Type, Any, Dict, List, Callable, Optional, Union

from ovos_bus_client import MessageBusClient, Message
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG
from pydantic import BaseModel


# Base Pydantic Model for Tool Input/Arguments
class ToolArguments(BaseModel):
    """Base class for Pydantic models defining tool input/arguments."""
    pass


# Base Pydantic Model for Tool Output
class ToolOutput(BaseModel):
    """Base class for Pydantic models defining tool output structure."""
    pass


# --- Type Aliases for Clarity ---
ToolCallReturn = Union[Dict[str, Any], ToolOutput]
ToolCallFunc = Callable[[ToolArguments], ToolCallReturn]


@dataclass
class AgentTool:
    """
    Defines a single executable function (tool) available to an Agent.

    This dataclass provides the necessary structured metadata (schemas)
    for LLM communication, paired with the actual executable Python logic.
    """
    name: str = field(metadata={'help': 'The unique, snake_case name of the tool (used by the LLM).'})
    description: str = field(metadata={'help': 'A detailed, natural language description of the tool\'s purpose.'})
    argument_schema: Type[ToolArguments] = field(metadata={'help': 'Pydantic model defining the expected input/arguments.'})
    output_schema: Type[ToolOutput] = field(metadata={'help': 'Pydantic model defining the expected output structure.'})
    tool_call: ToolCallFunc = field(
        metadata={'help': 'The function to execute the tool logic. It accepts one positional argument (an instantiated ToolArguments model) and must return a Dict[str, Any] or an instantiated ToolOutput model.'}
    )


class ToolBox(ABC):
    """
    Abstract base class for a ToolBox plugin.

    Each ToolBox is a discoverable plugin that groups related AgentTools. It exposes
    tools as services over the OVOS messagebus and provides a direct execution interface.

    Entry point group: ``opm.agents.toolbox``
    """

    def __init__(self,
                 toolbox_id: str,
                 config: Optional[Dict[str, Any]] = None,
                 bus: Optional[Union[MessageBusClient, FakeBus]] = None):
        """
        Initializes the ToolBox. Note: Messagebus binding is deferred until `bind()` is called.

        Args:
            toolbox_id: Unique plugin identity, matching its entry-point name.
            config: Plugin-specific configuration dict.
            bus: The OVOS Messagebus client instance. If provided, `bind()` is called automatically.
        """
        self.toolbox_id: str = toolbox_id
        self.config: Dict[str, Any] = config or {}
        self.bus: Optional[Union[MessageBusClient, FakeBus]] = None

        # Internal cache for discovered tools, mapped by name
        self.tools: Dict[str, AgentTool] = {}
        try:
            self.tools = {tool.name: tool for tool in self.discover_tools()}
        except Exception as e:
            LOG.debug(f"ToolBox '{self.toolbox_id}' deferred tool discovery: {e}")

        # Initialize the messagebus connection if provided
        if bus:
            self.bind(bus)

    def bind(self, bus: Union[MessageBusClient, FakeBus]) -> None:
        """
        Binds the ToolBox to a specific Messagebus instance and registers handlers.

        This method must be called to enable messagebus-based discovery and calling.

        Args:
            bus: The active OVOS Messagebus client or FakeBus instance.
        """
        self.bus = bus
        # General discovery broadcast
        self.bus.on("ovos.persona.tools.discover", self.handle_discover)
        # Specific call channel for this toolbox
        self.bus.on(f"ovos.persona.tools.{self.toolbox_id}.call", self.handle_call)

    def refresh_tools(self) -> None:
        """
        Reloads and updates the internal cache of AgentTools by calling
        the abstract `discover_tools` method. This is implicitly called
        if a tool is requested but not found in the cache.
        """
        self.tools = {tool.name: tool for tool in self.discover_tools()}

    def handle_discover(self, message: Message) -> None:
        """
        Handles the 'ovos.persona.tools.discover' messagebus event.

        Emits a response containing the full list of tools provided by this ToolBox,
        including JSON Schemas for arguments and output.

        Args:
            message: The incoming discovery Message object.
        """
        self.refresh_tools()
        response_data: Dict[str, Any] = {
            "tools": self.tool_json_list,
            "toolbox_id": self.toolbox_id
        }
        self.bus.emit(message.response(response_data))

    def handle_call(self, message: Message) -> None:
        """
        Handles messagebus calls to a specific tool within this ToolBox.

        It attempts to execute the tool and emits the result or error back on the bus.

        Args:
            message: The incoming Message object containing 'name' (tool name)
                     and 'kwargs' (tool arguments dictionary).
        """
        name: str = message.data.get("name", "")
        tool_kwargs: Dict[str, Any] = message.data.get("kwargs", {})

        try:
            # Use the execution wrapper method
            result: ToolOutput = self.call_tool(name, tool_kwargs)
            self.bus.emit(message.response({"result": result.model_dump(mode='json'), "toolbox_id": self.toolbox_id}))
        except Exception as e:
            # Catch all execution exceptions (including ValueErrors from call_tool)
            error: str = f"{type(e).__name__}: {str(e)}"
            self.bus.emit(message.response({"error": error, "toolbox_id": self.toolbox_id}))

    @staticmethod
    def validate_input(tool: AgentTool, tool_kwargs: Dict[str, Any]) -> ToolArguments:
        """
        Validates raw keyword arguments against the tool's input schema.

        Args:
            tool: The :class:`AgentTool` definition.
            tool_kwargs: The raw dictionary of arguments.

        Returns:
            An instantiated :class:`ToolArguments` Pydantic model.

        Raises:
            ValueError: If input validation fails (e.g., missing fields, wrong types).
        """
        try:
            ArgsModel: Type[ToolArguments] = tool.argument_schema
            # Instantiating the Pydantic model implicitly validates the input
            return ArgsModel(**tool_kwargs)
        except Exception as e:
            raise ValueError(f"Invalid input for '{tool.name}'") from e

    @staticmethod
    def validate_output(tool: AgentTool, raw_result: Dict[str, Any]) -> ToolOutput:
        """
        Validates the raw dictionary output from the tool execution against the output schema.

        Args:
            tool: The :class:`AgentTool` definition.
            raw_result: The raw dictionary returned by the tool's execution function.

        Returns:
            An instantiated :class:`ToolOutput` Pydantic model.

        Raises:
            ValueError: If output validation fails.
        """
        try:
            OutputModel: Type[ToolOutput] = tool.output_schema
            # Validate the raw result against the output schema.
            # The .model_validate() method returns a validated Pydantic object
            return OutputModel.model_validate(raw_result)
        except Exception as e:
            raise ValueError(f"Invalid output from '{tool.name}'") from e

    def call_tool(self, name: str, tool_kwargs: Union[ToolArguments, Dict[str, Any]]) -> ToolOutput:
        """
        Direct execution interface for an Agent (solver) to call a tool,
        with mandatory input and output validation.

        This method orchestrates the full lifecycle: retrieval, input validation,
        execution, and output validation.

        Args:
            name: The unique name of the tool to execute.
            tool_kwargs: Raw keyword arguments from the orchestrator.

        Returns:
            The validated :class:`ToolOutput` Pydantic object.

        Raises:
            ValueError: If the tool name is unknown or if input validation fails.
            RuntimeError: If tool execution or output validation fails.
        """
        tool: Optional[AgentTool] = self.get_tool(name)
        if not tool:
            raise ValueError(f"Unknown tool '{name}' for ToolBox '{self.toolbox_id}'.")

        # 1. Input Validation and Instantiation
        if isinstance(tool_kwargs, ToolArguments):
            # Case A: Input is an already validated Pydantic model.
            # We perform a quick type check to ensure it matches the declared schema.
            if not isinstance(tool_kwargs, tool.argument_schema):
                raise ValueError(
                    f"Tool '{name}' called with model of type {type(tool_kwargs).__name__}, "
                    f"but expected {tool.argument_schema.__name__}."
                )
            validated_args: ToolArguments = tool_kwargs
        elif isinstance(tool_kwargs, dict):
            # Case B: Input is a raw dictionary (needs validation).
            try:
                validated_args: ToolArguments = self.validate_input(tool, tool_kwargs)
            except ValueError as e:
                # Re-raise with more context
                raise ValueError(f"Tool input validation failed for '{name}' in ToolBox '{self.toolbox_id}'") from e
        else:
            # Case C: Input is an unexpected type.
            raise RuntimeError(
                f"Tool '{name}' called with unexpected type arguments: {type(tool_kwargs).__name__}. "
                "Must be Dict[str, Any] or ToolArguments."
            )

        try:
            # 2. Tool Execution
            raw_or_validated_result: ToolCallReturn = tool.tool_call(validated_args)
        except Exception as e:
            # Re-raise with more context
            raise RuntimeError(f"Tool execution failed for '{name}' in ToolBox '{self.toolbox_id}'") from e

        # 3. Output Validation/Casting
        if isinstance(raw_or_validated_result, ToolOutput):
            # Case A: Tool returned an already validated Pydantic model.
            # We perform a quick type check to ensure it matches the declared schema.
            if not isinstance(raw_or_validated_result, tool.output_schema):
                raise RuntimeError(
                    f"Tool '{name}' returned model of type {type(raw_or_validated_result).__name__}, "
                    f"but expected {tool.output_schema.__name__}."
                )
            return raw_or_validated_result
        elif isinstance(raw_or_validated_result, dict):
            # Case B: Tool returned a raw dictionary (needs validation).
            try:
                return self.validate_output(tool, raw_or_validated_result)
            except ValueError as e:
                # Catch Pydantic output ValidationErrors
                raise RuntimeError(f"Tool output validation failed for '{name}' in ToolBox '{self.toolbox_id}'") from e
        else:
            # Case C: Tool returned an unexpected type.
            raise RuntimeError(
                f"Tool '{name}' returned an unexpected type: {type(raw_or_validated_result).__name__}. "
                "Must return Dict[str, Any] or ToolOutput."
            )

    def get_tool(self, name: str) -> Optional[AgentTool]:
        """
        Retrieves an AgentTool definition by its name from the cache.

        Refreshes the tool cache if the tool is not found, ensuring lazy loading.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The AgentTool instance, or None if the tool does not exist.
        """
        if name not in self.tools:
            self.refresh_tools()
        return self.tools.get(name)

    @property
    def tool_json_list(self) -> List[Dict[str, Union[str, Dict[str, Any]]]]:
        """
        Generates a list of tool definitions with Pydantic schemas converted to JSON Schema.

        This output is suitable for direct transmission over the messagebus or
        for submission to an LLM's `functions` or `tools` API endpoint.

        Returns:
            A list of dictionaries, one for each tool, where `argument_schema`
            and `output_schema` are JSON Schema dictionaries.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                # Use Pydantic's .model_json_schema() for JSON schema export
                "argument_schema": tool.argument_schema.model_json_schema(),
                "output_schema": tool.output_schema.model_json_schema()
            }
            for tool in self.tools.values()
        ]

    @staticmethod
    def tools_to_openai_spec(tool_json_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert ``tool_json_list`` entries to the OpenAI ``tools`` spec.

        The OpenAI ``tools``/function-calling shape is the de-facto interchange
        format across providers (OpenAI, Ollama, llama.cpp, vLLM, …); each
        ChatEngine re-maps from this neutral spec to its own provider format.
        Static so callers can convert merged schemas from several toolboxes.

        Args:
            tool_json_list: Entries shaped like :attr:`tool_json_list` —
                ``{"name", "description", "argument_schema", "output_schema"}``.

        Returns:
            ``[{"type": "function", "function": {"name", "description",
            "parameters"}}]`` where ``parameters`` is the tool's
            ``argument_schema`` JSON Schema.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("argument_schema",
                                           {"type": "object", "properties": {}}),
                },
            }
            for tool in tool_json_list
        ]

    @property
    def openai_tools(self) -> List[Dict[str, Any]]:
        """This toolbox's tools as an OpenAI ``tools`` spec (see ``tools_to_openai_spec``)."""
        return self.tools_to_openai_spec(self.tool_json_list)

    @staticmethod
    def normalize_tools(
            tools: "Union[None, ToolBox, Dict[str, Any], List[Union[ToolBox, Dict[str, Any]]]]"
    ) -> List[Dict[str, Any]]:
        """Coerce tool input into the OpenAI ``tools`` spec list.

        Lets callers pass ``ToolBox`` objects directly (preferred) or
        already-built OpenAI tool dicts, or any mix in a list. ChatEngines call
        this on their ``tools`` argument so they accept both forms uniformly.

        Args:
            tools: A ``ToolBox``, an OpenAI tool dict, a list mixing either, or None.

        Returns:
            A flat list of OpenAI tool/function spec dicts (empty for None).
        """
        if tools is None:
            return []
        if isinstance(tools, ToolBox):
            return tools.openai_tools
        if isinstance(tools, dict):
            return [tools]
        specs: List[Dict[str, Any]] = []
        for t in tools:
            if isinstance(t, ToolBox):
                specs.extend(t.openai_tools)
            else:  # already an OpenAI tool dict
                specs.append(t)
        return specs
    @property
    def tool_json_list_compact(self) -> List[Dict[str, Union[str, Dict[str, Any]]]]:
        """
        Produce a compact list of tool definitions with minimized parameter schemas for use with smaller LLMs.
        
        Each item is a dict with keys:
        - `name`: tool name
        - `description`: tool description
        - `parameters`: the tool's argument JSON Schema with top-level `title` and `description` removed and `title` removed from each property to reduce payload size.
        
        Returns:
            List[Dict[str, Union[str, Dict[str, Any]]]]: Compact tool schema dictionaries.
        """
        compact = []
        for tool in self.tools.values():
            schema = tool.argument_schema.model_json_schema()
            # Strip bloat
            schema.pop("title", None)
            schema.pop("description", None)
            for prop in schema.get("properties", {}).values():
                prop.pop("title", None)
            compact.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": schema,
            })
        return compact

    @property
    def tool_openai_format(self) -> List[Dict[str, Any]]:
        """
        Tool definitions in OpenAI function-calling format.

        Suitable for passing as the ``tools`` parameter in
        ``/v1/chat/completions`` requests.

        Returns:
            List of OpenAI-format tool dicts.
        """
        tools = []
        for tool in self.tools.values():
            schema = tool.argument_schema.model_json_schema()
            schema.pop("title", None)
            schema.pop("description", None)
            for prop in schema.get("properties", {}).values():
                prop.pop("title", None)
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema,
                },
            })
        return tools

    # The only mandatory method for concrete plugins to implement
    @abstractmethod
    def discover_tools(self) -> List[AgentTool]:
        """
        Provide the list of AgentTool instances exposed by this toolbox.
        
        Implementations must return an idempotent list (safe to call multiple times) of the tools this plugin exposes.
        
        Returns:
            List[AgentTool]: Instantiated AgentTool objects provided by the toolbox.
        """
        raise NotImplementedError
