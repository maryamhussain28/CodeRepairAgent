"""The bounded repair loop: ask the model for one action, validate it, run it, repeat."""

import json

from core.models import ModelAction, RepairResult
from core.prompts import request_message, system_message, tool_result_message

MAX_DECISIONS = 8

# Required and optional fields per allowed tool, besides the always-present
# "tool" key and the always-optional "summary" key.
TOOL_FIELDS = {
    "read_file": {"path"},
    "run_tests": set(),
    "edit_file": {"path", "content"},
}


class InvalidActionError(Exception):
    """Raised when a model reply cannot be accepted as one allowed action."""


def _reject_duplicate_keys(pairs):
    """An object_pairs_hook that raises on a repeated key instead of keeping the last one."""
    seen = set()
    result = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key in reply: {key}")
        seen.add(key)
        result[key] = value
    return result


def _parse_action(raw: str) -> ModelAction:
    """Parse raw model text as exactly one allowed JSON action, or raise InvalidActionError."""
    try:
        parsed = json.loads(raw.strip(), object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidActionError(f"reply is not one valid JSON object: {exc}") from exc

    if not isinstance(parsed, dict):
        raise InvalidActionError("reply must be a JSON object, not a list or scalar")

    tool = parsed.get("tool")
    if tool not in TOOL_FIELDS:
        raise InvalidActionError(f"unknown tool: {tool!r}")

    required = TOOL_FIELDS[tool]
    allowed = required | {"tool", "summary"}
    present = set(parsed.keys())

    missing = required - present
    if missing:
        raise InvalidActionError(f"missing required field(s) for {tool}: {sorted(missing)}")

    extra = present - allowed
    if extra:
        raise InvalidActionError(f"field(s) not allowed for {tool}: {sorted(extra)}")

    arguments = {key: value for key, value in parsed.items() if key not in ("tool", "summary")}
    return ModelAction(tool=tool, arguments=arguments, summary=parsed.get("summary"))


class RepairAgent:
    """Traffic controller around a model: validates and bounds one repair attempt."""

    def __init__(self, client, tools, case_name: str, files: list[str]):
        self.client = client
        self.tools = tools
        self.case_name = case_name
        self.files = files

    def run(self) -> RepairResult:
        """Drive the bounded repair loop to completion and return the final result."""
        messages = [
            {"role": "system", "content": system_message()},
            {"role": "user", "content": request_message(self.case_name, self.files)},
        ]
        trace = [{"event": "repair_started", "case": self.case_name, "files": self.files}]

        did_read = False
        did_fail_test = False
        did_edit = False
        last_test_result = None
        changed_files: list[str] = []

        for _ in range(MAX_DECISIONS):
            try:
                raw_reply = self.client.chat(messages)
            except Exception as exc:
                trace.append({"event": "repair_finished", "passed": False, "reason": f"client error: {exc}"})
                return self._result(False, trace, changed_files, last_test_result)

            try:
                action = _parse_action(raw_reply)
            except InvalidActionError as exc:
                trace.append({"event": "model_response", "valid": False, "error": str(exc)})
                trace.append({"event": "repair_finished", "passed": False, "reason": f"invalid reply: {exc}"})
                return self._result(False, trace, changed_files, last_test_result)

            trace.append({"event": "model_response", "valid": True, "tool": action.tool, "summary": action.summary})
            messages.append({"role": "assistant", "content": raw_reply})

            if action.tool == "edit_file" and not (did_read and did_fail_test):
                observation = (
                    "Policy error: an edit is not allowed yet. Read a relevant file and "
                    "reproduce a failing test with run_tests first."
                )
                trace.append({"event": "tool_result", "tool": action.tool, "error": observation})
                messages.append({"role": "user", "content": tool_result_message(action.tool, observation)})
                continue

            try:
                if action.tool == "read_file":
                    observation = self.tools.read_file(action.arguments["path"])
                    did_read = True
                elif action.tool == "edit_file":
                    path = action.arguments["path"]
                    self.tools.edit_file(path, action.arguments["content"])
                    did_edit = True
                    if path not in changed_files:
                        changed_files.append(path)
                    observation = f"Saved changes to {path}"
                else:  # run_tests
                    test_result = self.tools.run_tests()
                    last_test_result = test_result
                    observation = test_result.output
            except Exception as exc:
                trace.append({"event": "tool_result", "tool": action.tool, "error": str(exc)})
                messages.append({"role": "user", "content": tool_result_message(action.tool, f"Error: {exc}")})
                continue

            trace.append({"event": "tool_result", "tool": action.tool, "observation": observation})

            if action.tool == "run_tests":
                if test_result.passed and did_edit:
                    trace.append({"event": "repair_finished", "passed": True, "reason": "tests pass after an edit"})
                    return self._result(True, trace, changed_files, last_test_result)
                if test_result.passed and not did_edit:
                    trace.append({
                        "event": "repair_finished",
                        "passed": False,
                        "reason": "no reproducible bug: tests already pass before any edit",
                    })
                    return self._result(False, trace, changed_files, last_test_result)
                did_fail_test = True

            messages.append({"role": "user", "content": tool_result_message(action.tool, observation)})

        trace.append({"event": "repair_finished", "passed": False, "reason": "decision budget exhausted"})
        return self._result(False, trace, changed_files, last_test_result)

    def _result(self, passed, trace, changed_files, last_test_result) -> RepairResult:
        return RepairResult(
            passed=passed,
            trace=trace,
            changed_files=changed_files,
            workspace=str(getattr(self.tools, "workspace", "")),
            last_test_result=last_test_result,
        )
