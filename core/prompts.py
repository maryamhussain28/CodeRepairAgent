"""Prompt text sent to the model: system instruction, case request, and tool results."""

SYSTEM_INSTRUCTION = """You are a focused Python repair agent.

Inspect the local code before changing anything. Reproduce a failing test by
running the project's tests before you edit any file. Make one focused edit
at a time. Verify the repair by running the tests again, and only report
success once they pass.

Reply with exactly one JSON object and nothing else: no Markdown, no prose,
no explanation outside the object. The optional "summary" field is a short
public label shown in the trace, not your private reasoning.

Allowed actions:
{"tool":"read_file","path":"test_calculator.py","summary":"Read the test"}
{"tool":"run_tests","summary":"Reproduce the failure"}
{"tool":"edit_file","path":"calculator.py","content":"..."}
"""


def system_message() -> str:
    """Return the fixed system instruction sent at the start of every repair."""
    return SYSTEM_INSTRUCTION


def request_message(case_name: str, files: list[str]) -> str:
    """Describe the selected case and its visible files, and ask for the next action."""
    file_list = "\n".join(f"- {name}" for name in files)
    return (
        f"Selected project: {case_name}\n"
        f"Visible files in the workspace:\n{file_list}\n\n"
        "What is the next action?"
    )


def tool_result_message(tool: str, observation: str) -> str:
    """Report one tool's observation back to the model and ask for the next action."""
    return f"Result of {tool}:\n{observation}\n\nWhat is the next action?"
