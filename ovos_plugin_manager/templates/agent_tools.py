from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Type, Any, Dict, List, Callable, Optional, Union

from ovos_bus_client import MessageBusClient, Message
from ovos_utils.fakebus import FakeBus
from pydantic import BaseModel, Field



# Base Pydantic Model for Tool Input/Arguments
class ToolArguments(BaseModel):
    """Base class for Pydantic models defining tool input/arguments."""
    pass


# Base Pydantic Model for Tool Output
class ToolOutput(BaseModel):
    """Base class for Pydantic models defining tool output structure."""
    pass

# --- Type Aliases for Clarity ---
ToolCallFunc = Callable[[ToolArguments], Dict[str, Any]]


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
        metadata={'help': 'The function to execute the tool logic. It accepts one positional argument (an instantiated ToolArguments model) and must return a Dict[str, Any] conforming to output_schema.'}
    )

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
            result: ToolOutput = self.call_tool(name, tool_kwargs)
            self.bus.emit(message.response({"result": result.model_dump(), "toolbox_id": self.toolbox_id}))
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
            raise ValueError(f"Invalid input for '{tool.name}': {tool_kwargs}") from e

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
            raise ValueError(f"Invalid output from '{tool.name}': {raw_result}") from e


    def call_tool(self, name: str, tool_kwargs: Dict[str, Any]) -> ToolOutput:
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
        if tool:
            try:
                # 1. Input Validation and Instantiation
                validated_args: ToolArguments = self.validate_input(tool, tool_kwargs)
            except ValueError as e:
                # Re-raise with more context
                raise ValueError(f"Tool input validation failed for '{name}' in ToolBox '{self.toolbox_id}'") from e

            try:
                # 2. Tool Execution
                raw_result: Dict[str, Any] = tool.tool_call(validated_args)
            except Exception as e:
                # Catch execution errors
                raise RuntimeError(f"Tool execution failed for '{name}' in ToolBox '{self.toolbox_id}'") from e

            try:
                # 3. Output Validation
                return self.validate_output(tool, raw_result)
            except ValueError as e:
                # Catch Pydantic output ValidationErrors
                raise RuntimeError(f"Tool output validation failed for '{name}' in ToolBox '{self.toolbox_id}'") from e
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
                # Use Pydantic's .model_json_schema() for JSON schema export
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
