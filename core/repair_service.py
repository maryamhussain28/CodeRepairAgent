"""Selects an allowed evaluation project, creates its disposable workspace, and runs the agent.

This module stays in core/: it never imports adapters/ directly. The Docker
workspace copy and the concrete repair tools are supplied as factories by
bootstrap.py, the one place allowed to connect core/ to adapters/.
"""

from pathlib import Path

from core.models import RepairResult
from core.repair_agent import RepairAgent

EVALS_ROOT = Path("evals").resolve()


class UnknownCaseError(Exception):
    """Raised when the selected path is not one of the supplied evals/ projects."""


def _resolve_case_dir(selected_path: str) -> Path:
    """Validate that selected_path names one existing evals/<case> directory."""
    candidate = Path(selected_path)
    if candidate.is_absolute():
        raise UnknownCaseError(f"absolute paths are not allowed: {selected_path}")

    resolved = (Path.cwd() / candidate).resolve()
    if resolved.parent != EVALS_ROOT or not resolved.is_dir():
        raise UnknownCaseError(f"unknown evaluation project: {selected_path}")
    return resolved


class RepairService:
    """Builds and runs one repair attempt for a selected evals/<case> project."""

    def __init__(self, client_factory, workspace_factory, tools_factory):
        # client_factory(case_name) -> ChatClient: each case gets its own
        # prepared scripted sequence (or, later, a live model client).
        # workspace_factory(case_dir) -> Path: makes the disposable copy.
        # tools_factory(workspace) -> RepairToolsPort: wraps that copy.
        self.client_factory = client_factory
        self.workspace_factory = workspace_factory
        self.tools_factory = tools_factory

    def repair(self, selected_path: str) -> RepairResult:
        """Copy the selected case into a disposable workspace and run the repair agent."""
        case_dir = _resolve_case_dir(selected_path)
        workspace = self.workspace_factory(case_dir)
        files = sorted(entry.name for entry in workspace.iterdir() if entry.is_file())

        tools = self.tools_factory(workspace)
        client = self.client_factory(case_dir.name)
        agent = RepairAgent(client, tools, case_dir.name, files)
        return agent.run()
