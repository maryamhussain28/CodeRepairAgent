"""Shared result and action shapes used across the repair agent."""

from dataclasses import dataclass, field


@dataclass
class TestResult:
    """Outcome of one sandboxed pytest run."""

    __test__ = False  # tell pytest this is not a test class

    passed: bool
    output: str
    returncode: int


@dataclass
class ModelAction:
    """One tool call requested by the model."""

    tool: str
    arguments: dict
    summary: str | None = None


@dataclass
class RepairResult:
    """Final outcome returned by the repair agent for one project."""

    passed: bool
    trace: list = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    workspace: str = ""
    last_test_result: TestResult | None = None
