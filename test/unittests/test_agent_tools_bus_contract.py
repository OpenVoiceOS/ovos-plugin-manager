"""ToolBox bus surface against OVOS-TOOLS-1 §3, §4 and §6.

Each check drives a real FakeBus with one hosted toolbox that owns one tool
and asserts the payload values, the count of responses, and silence where the
specification requires it (§7).
"""
import unittest
from typing import List

from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus
from pydantic import Field

from ovos_plugin_manager.templates.agent_tools import (
    AgentTool, ToolArguments, ToolBox, ToolOutput,
)


class WordArgs(ToolArguments):
    word: str = Field(..., description="A word")


class LengthOut(ToolOutput):
    length: int


class WordToolBox(ToolBox):
    def __init__(self, bus=None, toolbox_id="wordnet"):
        self.runs: List[str] = []
        self.discoveries = 0
        super().__init__(toolbox_id=toolbox_id, bus=bus)

    def _length(self, args: WordArgs) -> LengthOut:
        self.runs.append(args.word)
        return LengthOut(length=len(args.word))

    def discover_tools(self) -> List[AgentTool]:
        self.discoveries += 1
        return [AgentTool(name="word_length", description="Length of a word.",
                          argument_schema=WordArgs, output_schema=LengthOut,
                          tool_call=self._length)]


def _answers(bus, topic, data=None):
    got = []
    handler = got.append
    bus.on(topic + ".response", handler)
    bus.emit(Message(topic, data or {}))
    bus.remove(topic + ".response", handler)
    return [m.data for m in got]


class TestToolsBusContract(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.toolbox = WordToolBox(bus=self.bus)

    def test_discover_tool_definitions_carry_toolbox_id(self):
        answers = _answers(self.bus, "ovos.persona.tools.discover")
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0]["toolbox_id"], "wordnet")
        tool = answers[0]["tools"][0]
        self.assertEqual(sorted(tool), ["argument_schema", "description", "name", "output_schema", "toolbox_id"])
        self.assertEqual((tool["name"], tool["toolbox_id"]), ("word_length", "wordnet"))

    def test_static_call_topic_answers_once_with_result(self):
        answers = _answers(self.bus, "ovos.persona.tools.call",
                           {"toolbox_id": "wordnet", "name": "word_length", "kwargs": {"word": "serendipity"}})
        self.assertEqual(answers, [{"result": {"length": 11}, "toolbox_id": "wordnet"}])

    def test_static_call_error_for_unknown_tool(self):
        answers = _answers(self.bus, "ovos.persona.tools.call",
                           {"toolbox_id": "wordnet", "name": "nope", "kwargs": {}})
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0]["toolbox_id"], "wordnet")
        self.assertNotIn("result", answers[0])
        self.assertTrue(answers[0]["error"].startswith("ValueError: Unknown tool 'nope'"))

    def test_static_call_for_another_toolbox_is_silent(self):
        self.assertEqual(_answers(self.bus, "ovos.persona.tools.call",
                                  {"toolbox_id": "other", "name": "word_length", "kwargs": {"word": "x"}}), [])

    def test_static_call_compares_toolbox_id_exactly(self):
        bus = FakeBus()
        host = WordToolBox(bus=bus, toolbox_id="rv-text-a")
        for other in ("rv-text", "rv-text-ab", "RV-TEXT-A", "rv-text-a "):
            self.assertEqual(_answers(bus, "ovos.persona.tools.call",
                                      {"toolbox_id": other, "name": "word_length", "kwargs": {"word": "x"}}), [])
        self.assertEqual(host.runs, [])
        self.assertEqual(len(_answers(bus, "ovos.persona.tools.call",
                                      {"toolbox_id": "rv-text-a", "name": "word_length", "kwargs": {"word": "x"}})), 1)
        self.assertEqual(host.runs, ["x"])

    def test_static_call_naming_no_toolbox_is_silent(self):
        self.assertEqual(_answers(self.bus, "ovos.persona.tools.call",
                                  {"name": "word_length", "kwargs": {"word": "x"}}), [])

    def test_predecessor_topic_still_answers(self):
        answers = _answers(self.bus, "ovos.persona.tools.wordnet.call",
                           {"name": "word_length", "kwargs": {"word": "abc"}})
        self.assertEqual(answers, [{"result": {"length": 3}, "toolbox_id": "wordnet"}])

    def test_unbind_stops_every_answer(self):
        self.toolbox.unbind()
        # an answer can be lost after the tool ran, so count the runs as well
        for topic, data in (("ovos.persona.tools.call", {"toolbox_id": "wordnet"}),
                            ("ovos.persona.tools.wordnet.call", {})):
            self.bus.emit(Message(topic, {**data, "name": "word_length", "kwargs": {"word": "x"}}))
        self.assertEqual(self.toolbox.runs, [])
        # a discover answer can be lost too; handle_discover refreshes the tools first
        discoveries = self.toolbox.discoveries
        self.bus.emit(Message("ovos.persona.tools.discover"))
        self.assertEqual(self.toolbox.discoveries, discoveries)
        self.assertIsNone(self.toolbox.bus)
        self.assertEqual(_answers(self.bus, "ovos.persona.tools.discover"), [])
        self.assertEqual(_answers(self.bus, "ovos.persona.tools.call",
                                  {"toolbox_id": "wordnet", "name": "word_length", "kwargs": {"word": "x"}}), [])
        self.assertEqual(_answers(self.bus, "ovos.persona.tools.wordnet.call",
                                  {"name": "word_length", "kwargs": {"word": "x"}}), [])
