"""Assembly point: the only module that imports both core/ and adapters/.

Connects a model provider, the Docker-backed sandbox tools, and the repair
service. core/ never imports from here or from adapters/ directly.
"""

import json

from adapters.models.scripted import ScriptedClient
from adapters.sandbox import runner
from adapters.sandbox.repair_tools import RepairTools
from core.repair_service import RepairService


def _action(tool: str, summary: str, **fields) -> str:
    """Build one valid JSON action string for a scripted sequence."""
    return json.dumps({"tool": tool, "summary": summary, **fields})


ARITHMETIC_FIX = '''def add(left, right):
    """Return the sum of two numbers."""
    return left + right
'''

BRACKETS_FIX = '''def is_balanced(text):
    """Return whether parentheses, brackets, and braces are properly nested."""
    opening = "([{"
    closing = ")]}"
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []

    for character in text:
        if character in opening:
            stack.append(character)
        elif character in closing:
            if not stack or stack.pop() != pairs[character]:
                return False

    return not stack
'''

MEDIAN_FIX = '''def median(values):
    """Return the median value without changing the input sequence."""
    ordered = sorted(values)
    length = len(ordered)
    middle = length // 2
    if length % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2
'''

TEXT_TOOLS_FIX = '''def normalize_name(name):
    """Trim surrounding whitespace and lowercase a supplied name."""
    return name.strip().lower()


def greeting(name):
    """Create a greeting from a normalized name."""
    return f"Hello, {normalize_name(name).capitalize()}!"


def initials(name):
    """Return uppercase initials for the whitespace-separated parts of a name."""
    return "".join(part[0].upper() for part in name.split())
'''

WORD_TOOLS_FIX = '''def unique_words(text):
    """Return lowercase words once, in the order first seen."""
    seen = []
    for word in text.lower().split():
        if word not in seen:
            seen.append(word)
    return seen
'''

# One valid read -> failing test -> edit -> passing test sequence per supplied
# case, so every dropdown choice (Task 6) has a prepared scripted repair.
SCRIPTED_SEQUENCES = {
    "arithmetic": [
        _action("read_file", "Read the test", path="test_calculator.py"),
        _action("run_tests", "Reproduce the failure"),
        _action("edit_file", "Fix add to use addition", path="calculator.py", content=ARITHMETIC_FIX),
        _action("run_tests", "Verify the repair"),
    ],
    "balanced_brackets": [
        _action("read_file", "Read the test", path="test_brackets.py"),
        _action("run_tests", "Reproduce the failure"),
        _action(
            "edit_file",
            "Check the matching bracket type before popping",
            path="brackets.py",
            content=BRACKETS_FIX,
        ),
        _action("run_tests", "Verify the repair"),
    ],
    "median": [
        _action("read_file", "Read the test", path="test_statistics_tools.py"),
        _action("run_tests", "Reproduce the failure"),
        _action(
            "edit_file",
            "Average the two middle values for even-length input",
            path="statistics_tools.py",
            content=MEDIAN_FIX,
        ),
        _action("run_tests", "Verify the repair"),
    ],
    "multi_function": [
        _action("read_file", "Read the test", path="test_text_tools.py"),
        _action("run_tests", "Reproduce the failure"),
        _action(
            "edit_file",
            "Capitalize the greeting name instead of upper-casing it",
            path="text_tools.py",
            content=TEXT_TOOLS_FIX,
        ),
        _action("run_tests", "Verify the repair"),
    ],
    "unique_words": [
        _action("read_file", "Read the test", path="test_word_tools.py"),
        _action("run_tests", "Reproduce the failure"),
        _action(
            "edit_file",
            "Preserve first-appearance order instead of sorting",
            path="word_tools.py",
            content=WORD_TOOLS_FIX,
        ),
        _action("run_tests", "Verify the repair"),
    ],
}


def _scripted_client_factory(case_name: str) -> ScriptedClient:
    """Return a fresh ScriptedClient holding the prepared sequence for one case."""
    try:
        replies = SCRIPTED_SEQUENCES[case_name]
    except KeyError as exc:
        raise ValueError(f"no scripted sequence prepared for case: {case_name}") from exc
    return ScriptedClient(replies)


def build_repair_service(provider: str) -> RepairService:
    """Create the RepairService wired to the selected model provider."""
    if provider == "scripted":
        client_factory = _scripted_client_factory
    else:
        raise ValueError(f"unknown provider: {provider}")

    return RepairService(
        client_factory=client_factory,
        workspace_factory=runner.create_workspace,
        tools_factory=RepairTools,
    )
