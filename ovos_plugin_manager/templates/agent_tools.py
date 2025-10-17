from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Type, Any, Dict, List, Callable, Optional, Union

from ovos_bus_client import MessageBusClient, Message
from ovos_utils.fakebus import FakeBus
from pydantic import BaseModel, Field


# Base Pydantic Model for Tool Input/Arguments
class ToolArguments(BaseModel):
    """Base class for Pydantic models defining tool arguments."""
    pass


# Base Pydantic Model for Tool Output
class ToolOutput(BaseModel):
    """Base class for Pydantic models defining tool output structure."""
    pass


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
    tool_call: Callable[..., Dict[str, Any]] = field(metadata={'help': 'The function to execute the tool logic. It accepts keyword arguments validated against argument_schema and must return a Dict[str, Any] conforming to output_schema.'})


class ToolBox(ABC):
    """
    Abstract base class for a ToolBox plugin.

    Each ToolBox is a discoverable plugin that groups related AgentTools. It exposes
    tools as services over the OVOS messagebus and provides a direct execution interface.
    """

    def __init__(self, toolbox_id: str,
                 bus: Optional[Union[MessageBusClient, FakeBus]] = None):
        """
        Initializes the ToolBox. Note: Messagebus binding is deferred until `bind()` is called.

        Args:
            toolbox_id: A unique identifier for this ToolBox instance (usually the entrypoint name, e.g., 'web_search_tools').
            bus: The OVOS Messagebus client instance. If provided, `bind()` is called automatically.
        """
        self.toolbox_id: str = toolbox_id  # Unique ID for the toolbox
        self.bus: Optional[Union[MessageBusClient, FakeBus]] = None

        # Internal cache for discovered tools, mapped by name
        self.tools: Dict[str, AgentTool] = {}
        try:
            self.discover_tools() # try to find tools immediately
        except Exception as e:
            pass  # will be lazy loaded or throw error on first usage

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
            result: Dict[str, Any] = self.call_tool(name, tool_kwargs)
            self.bus.emit(message.response({"result": result, "toolbox_id": self.toolbox_id}))
        except Exception as e:
            # Catch all execution exceptions (including ValueErrors from call_tool)
            error: str = f"{type(e).__name__}: {str(e)}"
            self.bus.emit(message.response({"error": error, "toolbox_id": self.toolbox_id}))

    def call_tool(self, name: str, tool_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Direct execution interface for an Agent (solver) to call a tool.

        This path is used by the `ovos-solver-tool-orchestrator-plugin` for direct,
        in-process execution without messagebus overhead.

        Args:
            name: The unique name of the tool to execute.
            tool_kwargs: Keyword arguments for the tool, expected to be validated by the caller.

        Returns:
            The raw dictionary output from the tool's `tool_call` function.

        Raises:
            ValueError: If the requested tool name is unknown for this ToolBox.
            RuntimeError: If the execution of the tool's `tool_call` function fails.
        """
        tool: Optional[AgentTool] = self.get_tool(name)
        if tool:
            try:
                # Execution assumes kwargs are already validated/sanitized by the orchestrator
                return tool.tool_call(**tool_kwargs)
            except Exception as e:
                # Wrap tool execution errors for better context
                raise RuntimeError(f"Tool execution failed for '{name}' in ToolBox '{self.toolbox_id}'") from e
        else:
            raise ValueError(f"Unknown tool '{name}' for ToolBox '{self.toolbox_id}'.")

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
                "argument_schema": tool.argument_schema.model_json_schema(),
                "output_schema": tool.output_schema.model_json_schema()
            }
            for tool in self.tools.values()
        ]

    # The only mandatory method for concrete plugins to implement
    @abstractmethod
    def discover_tools(self) -> List[AgentTool]:
        """
        Abstract method to be implemented by concrete ToolBox plugins.

        This method must define and return the list of AgentTools provided by this plugin.
        The implementation should be idempotent (safe to call multiple times).

        Returns:
            A list of instantiated AgentTool objects.
        """
        raise NotImplementedError
