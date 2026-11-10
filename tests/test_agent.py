"""Unit tests for the bounded repair loop, using ScriptedClient and fake tools."""

import pytest

from adapters.models.scripted import ScriptedClient
from core.models import TestResult
from core.repair_agent import RepairAgent


class FakeTools:
    """A controllable stand-in for RepairToolsPort; no files, no Docker."""

    def __init__(self, read_file_responses=None, run_tests_responses=None):
        self.workspace = "fake-workspace"
        self.read_file_calls = []
        self.edit_file_calls = []
        self.run_tests_calls = 0
        self._read_file_responses = read_file_responses or {}
        self._run_tests_responses = list(run_tests_responses or [])

    def read_file(self, path):
        self.read_file_calls.append(path)
        return self._read_file_responses.get(path, "")

    def edit_file(self, path, content):
        self.edit_file_calls.append((path, content))

    def run_tests(self):
        self.run_tests_calls += 1
        if not self._run_tests_responses:
            raise RuntimeError("no more run_tests responses")
        return self._run_tests_responses.pop(0)


class FailingClient:
    """A ChatClient whose first call always raises, like a dropped connection."""

    def chat(self, messages):
        raise RuntimeError("model unavailable")


def test_read_then_failing_test_then_edit_then_passing_test_succeeds():
    replies = [
        '{"tool":"read_file","path":"test_calculator.py","summary":"Read the test"}',
        '{"tool":"run_tests","summary":"Reproduce the failure"}',
        '{"tool":"edit_file","path":"calculator.py","content":"def add(l, r): return l + r","summary":"Fix add"}',
        '{"tool":"run_tests","summary":"Verify the repair"}',
    ]
    tools = FakeTools(
        read_file_responses={"test_calculator.py": "def test_add(): assert add(2, 3) == 5"},
        run_tests_responses=[TestResult(False, "1 failed", 1), TestResult(True, "1 passed", 0)],
    )
    agent = RepairAgent(ScriptedClient(replies), tools, "arithmetic", ["calculator.py", "test_calculator.py"])

    result = agent.run()

    assert result.passed is True
    assert result.changed_files == ["calculator.py"]
    assert result.last_test_result.passed is True
    events = [entry["event"] for entry in result.trace]
    assert events[0] == "repair_started"
    assert events[-1] == "repair_finished"
    assert "model_response" in events
    assert "tool_result" in events


@pytest.mark.parametrize(
    "raw_reply",
    [
        "Sure, I will read the file next.",
        '```json\n{"tool":"run_tests"}\n```',
        '[{"tool":"run_tests"}]',
        '{"tool":"run_tests","tool":"edit_file"}',
        '{"tool":"delete_file"}',
        '{"tool":"read_file"}',
        '{"tool":"run_tests","path":"calculator.py"}',
    ],
)
def test_invalid_reply_calls_no_tool_and_fails(raw_reply):
    tools = FakeTools()
    agent = RepairAgent(ScriptedClient([raw_reply]), tools, "arithmetic", ["calculator.py"])

    result = agent.run()

    assert result.passed is False
    assert tools.read_file_calls == []
    assert tools.edit_file_calls == []
    assert tools.run_tests_calls == 0
    assert "invalid reply" in result.trace[-1]["reason"]


def test_edit_rejected_before_a_failing_test():
    replies = [
        '{"tool":"edit_file","path":"calculator.py","content":"def add(l, r): return l + r"}',
        '{"tool":"run_tests"}',
    ]
    tools = FakeTools(run_tests_responses=[TestResult(True, "2 passed", 0)])
    agent = RepairAgent(ScriptedClient(replies), tools, "arithmetic", ["calculator.py"])

    result = agent.run()

    assert tools.edit_file_calls == []
    assert result.passed is False
    assert any(entry.get("tool") == "edit_file" and "error" in entry for entry in result.trace)


def test_budget_exhaustion_stops_after_eight_decisions():
    replies = ['{"tool":"read_file","path":"a.py"}'] * 8
    tools = FakeTools(read_file_responses={"a.py": "value = 1"})
    agent = RepairAgent(ScriptedClient(replies), tools, "arithmetic", ["a.py"])

    result = agent.run()

    assert result.passed is False
    assert "budget" in result.trace[-1]["reason"]
    assert tools.read_file_calls == ["a.py"] * 8


def test_passing_baseline_is_not_reported_as_a_repair():
    tools = FakeTools(run_tests_responses=[TestResult(True, "3 passed", 0)])
    agent = RepairAgent(ScriptedClient(['{"tool":"run_tests"}']), tools, "arithmetic", ["calculator.py"])

    result = agent.run()

    assert result.passed is False
    assert result.last_test_result.passed is True
    assert result.changed_files == []
    assert "no reproducible bug" in result.trace[-1]["reason"]


def test_client_error_still_returns_a_repair_result():
    tools = FakeTools()
    agent = RepairAgent(FailingClient(), tools, "arithmetic", ["calculator.py"])

    result = agent.run()

    assert result.passed is False
    assert "client error" in result.trace[-1]["reason"]
