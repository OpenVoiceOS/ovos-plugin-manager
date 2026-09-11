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
import unittest
from typing import List
from unittest.mock import MagicMock, patch

from ovos_utils.fakebus import FakeBus
from pydantic import Field

from ovos_plugin_manager.templates.agent_tools import (
    AgentTool,
    ToolArguments,
    ToolBox,
    ToolOutput,
)


# ---------------------------------------------------------------------------
# Minimal concrete fixtures
# ---------------------------------------------------------------------------

class AddArgs(ToolArguments):
    a: int = Field(..., description="First operand.")
    b: int = Field(..., description="Second operand.")


class AddOutput(ToolOutput):
    result: int = Field(..., description="Sum of a and b.")


def add_logic(args: AddArgs) -> AddOutput:
    return AddOutput(result=args.a + args.b)


def failing_logic(args: AddArgs) -> AddOutput:
    raise RuntimeError("intentional failure")


class MathToolBox(ToolBox):
    def __init__(self, config=None, bus=None, fail_discover: bool = False):
        self._fail_discover = fail_discover
        super().__init__(toolbox_id="math_tools", config=config, bus=bus)

    def discover_tools(self) -> List[AgentTool]:
        if self._fail_discover:
            raise RuntimeError("discover failed")
        return [
            AgentTool(
                name="add",
                description="Add two integers.",
                argument_schema=AddArgs,
                output_schema=AddOutput,
                tool_call=add_logic,
            )
        ]


class FailingToolBox(ToolBox):
    def __init__(self, config=None, bus=None):
        super().__init__(toolbox_id="failing_tools", config=config, bus=bus)

    def discover_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="fail",
                description="Always raises.",
                argument_schema=AddArgs,
                output_schema=AddOutput,
                tool_call=failing_logic,
            )
        ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAgentToolDataclass(unittest.TestCase):
    def setUp(self):
        self.tool = AgentTool(
            name="add",
            description="Add two integers.",
            argument_schema=AddArgs,
            output_schema=AddOutput,
            tool_call=add_logic,
        )

    def test_fields(self):
        self.assertEqual(self.tool.name, "add")
        self.assertEqual(self.tool.argument_schema, AddArgs)
        self.assertEqual(self.tool.output_schema, AddOutput)

    def test_tool_call_executes(self):
        result = self.tool.tool_call(AddArgs(a=2, b=3))
        self.assertEqual(result.result, 5)


class TestToolBoxInit(unittest.TestCase):
    def test_tools_populated_on_init(self):
        tb = MathToolBox()
        self.assertIn("add", tb.tools)

    def test_failed_discover_logs_and_continues(self):
        with patch("ovos_plugin_manager.templates.agent_tools.LOG") as mock_log:
            tb = MathToolBox(fail_discover=True)
            mock_log.debug.assert_called_once()
        self.assertEqual(tb.tools, {})

    def test_bus_bind_on_init(self):
        bus = FakeBus()
        tb = MathToolBox(bus=bus)
        self.assertIs(tb.bus, bus)

    def test_no_bus_on_init(self):
        tb = MathToolBox()
        self.assertIsNone(tb.bus)


class TestToolBoxContract(unittest.TestCase):
    def test_config_passthrough(self):
        cfg = {"api_key": "secret", "some_option": 42}
        tb = MathToolBox(config=cfg)
        self.assertEqual(tb.config, cfg)

    def test_config_defaults_to_empty_dict(self):
        tb = MathToolBox()
        self.assertEqual(tb.config, {})

    def test_config_and_bus_together(self):
        bus = FakeBus()
        tb = MathToolBox(config={"x": 1}, bus=bus)
        self.assertEqual(tb.config, {"x": 1})
        self.assertIs(tb.bus, bus)


class TestToolBoxCallTool(unittest.TestCase):
    def setUp(self):
        self.tb = MathToolBox()

    def test_call_with_dict(self):
        result = self.tb.call_tool("add", {"a": 3, "b": 4})
        self.assertIsInstance(result, AddOutput)
        self.assertEqual(result.result, 7)

    def test_call_with_pydantic_model(self):
        args = AddArgs(a=10, b=20)
        result = self.tb.call_tool("add", args)
        self.assertEqual(result.result, 30)

    def test_call_unknown_tool_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.tb.call_tool("nonexistent", {"a": 1, "b": 2})

    def test_call_invalid_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.tb.call_tool("add", {"a": "not_an_int", "b": 2})

    def test_call_wrong_pydantic_type_raises_value_error(self):
        class OtherArgs(ToolArguments):
            x: int = Field(...)

        with self.assertRaises(ValueError):
            self.tb.call_tool("add", OtherArgs(x=1))

    def test_call_unexpected_kwarg_type_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            self.tb.call_tool("add", "not_a_dict_or_model")

    def test_execution_failure_raises_runtime_error(self):
        tb = FailingToolBox()
        with self.assertRaises(RuntimeError):
            tb.call_tool("fail", {"a": 1, "b": 2})


class TestToolBoxDiscovery(unittest.TestCase):
    def test_refresh_tools(self):
        tb = MathToolBox()
        tb.tools = {}  # clear cache
        tb.refresh_tools()
        self.assertIn("add", tb.tools)

    def test_get_tool_lazy_refresh(self):
        tb = MathToolBox()
        tb.tools = {}  # simulate empty cache
        tool = tb.get_tool("add")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "add")

    def test_get_tool_missing_returns_none(self):
        tb = MathToolBox()
        result = tb.get_tool("nonexistent")
        self.assertIsNone(result)


class TestToolJsonList(unittest.TestCase):
    def test_json_list_structure(self):
        tb = MathToolBox()
        lst = tb.tool_json_list
        self.assertEqual(len(lst), 1)
        entry = lst[0]
        self.assertEqual(entry["name"], "add")
        self.assertIn("argument_schema", entry)
        self.assertIn("output_schema", entry)
        # JSON schema format
        self.assertIn("properties", entry["argument_schema"])

    def test_json_list_empty_when_no_tools(self):
        tb = MathToolBox(fail_discover=True)
        self.assertEqual(tb.tool_json_list, [])


class TestToolsToOpenAISpec(unittest.TestCase):
    def test_staticmethod_shape(self):
        spec = ToolBox.tools_to_openai_spec([
            {"name": "add", "description": "Add two ints.",
             "argument_schema": {"type": "object", "properties": {"a": {"type": "integer"}}},
             "output_schema": {}},
        ])
        self.assertEqual(spec[0]["type"], "function")
        fn = spec[0]["function"]
        self.assertEqual(fn["name"], "add")
        self.assertEqual(fn["description"], "Add two ints.")
        # parameters is exactly the argument_schema
        self.assertEqual(fn["parameters"]["properties"]["a"]["type"], "integer")

    def test_missing_description_and_schema_defaults(self):
        spec = ToolBox.tools_to_openai_spec([{"name": "noop"}])
        self.assertEqual(spec[0]["function"]["description"], "")
        self.assertEqual(spec[0]["function"]["parameters"],
                         {"type": "object", "properties": {}})

    def test_openai_tools_property(self):
        tb = MathToolBox()
        spec = tb.openai_tools
        self.assertEqual(spec[0]["function"]["name"], "add")
        self.assertEqual(spec, ToolBox.tools_to_openai_spec(tb.tool_json_list))


class TestNormalizeTools(unittest.TestCase):
    def test_none(self):
        self.assertEqual(ToolBox.normalize_tools(None), [])

    def test_single_toolbox(self):
        tb = MathToolBox()
        self.assertEqual(ToolBox.normalize_tools(tb), tb.openai_tools)

    def test_single_dict(self):
        spec = {"type": "function", "function": {"name": "x"}}
        self.assertEqual(ToolBox.normalize_tools(spec), [spec])

    def test_list_of_toolboxes(self):
        tb = MathToolBox()
        self.assertEqual(ToolBox.normalize_tools([tb]), tb.openai_tools)

    def test_mixed_list(self):
        tb = MathToolBox()
        extra = {"type": "function", "function": {"name": "x"}}
        out = ToolBox.normalize_tools([tb, extra])
        self.assertEqual(out, tb.openai_tools + [extra])


class TestToolBoxBusHandlers(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.tb = MathToolBox(bus=self.bus)

    def test_handle_discover_emits_response(self):
        responses = []
        self.bus.on("ovos.persona.tools.discover.response",
                    lambda m: responses.append(m))
        from ovos_bus_client import Message
        self.bus.emit(Message("ovos.persona.tools.discover"))
        self.bus.wait_for_response  # FakeBus is synchronous
        # handler emits response directly
        self.assertEqual(len(responses), 1)
        self.assertIn("tools", responses[0].data)
        self.assertEqual(responses[0].data["toolbox_id"], "math_tools")

    def test_handle_call_success(self):
        responses = []
        self.bus.on("ovos.persona.tools.math_tools.call.response",
                    lambda m: responses.append(m))
        from ovos_bus_client import Message
        self.bus.emit(Message("ovos.persona.tools.math_tools.call",
                               {"name": "add", "kwargs": {"a": 5, "b": 6}}))
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].data["result"]["result"], 11)

    def test_handle_call_error(self):
        responses = []
        self.bus.on("ovos.persona.tools.math_tools.call.response",
                    lambda m: responses.append(m))
        from ovos_bus_client import Message
        self.bus.emit(Message("ovos.persona.tools.math_tools.call",
                               {"name": "nonexistent", "kwargs": {}}))
        self.assertEqual(len(responses), 1)
        self.assertIn("error", responses[0].data)


if __name__ == "__main__":
    unittest.main()
