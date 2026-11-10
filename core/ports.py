"""Capability contracts the repair agent depends on, not their implementations."""

from typing import Protocol

from core.models import TestResult


class ChatClient(Protocol):
    """Anything that can turn a message history into one text reply."""

    def chat(self, messages: list[dict]) -> str:
        ...


class RepairToolsPort(Protocol):
    """The three operations the repair agent may perform on a workspace.

    Named with a Port suffix because Task 2 supplies the concrete
    implementation, RepairTools, that satisfies this contract.
    """

    def read_file(self, path: str) -> str:
        ...

    def edit_file(self, path: str, content: str) -> None:
        ...

    def run_tests(self) -> TestResult:
        ...


class TraceRecorder(Protocol):
    """Optional hook for recording one public trace event."""

    def record(self, event: str, payload: dict) -> None:
        ...
