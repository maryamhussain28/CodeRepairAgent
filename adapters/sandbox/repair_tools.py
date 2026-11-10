"""Safe file and test operations confined to one disposable workspace."""

from pathlib import Path

from adapters.sandbox import runner
from core.models import TestResult


def safe_path(workspace: Path, requested_path: str) -> Path:
    """Resolve requested_path inside workspace; reject escapes and absolute paths."""
    if Path(requested_path).is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {requested_path}")
    workspace_resolved = workspace.resolve()
    candidate = (workspace_resolved / requested_path).resolve()
    if candidate != workspace_resolved and workspace_resolved not in candidate.parents:
        raise ValueError(f"Path escapes the workspace: {requested_path}")
    return candidate


class RepairTools:
    """Concrete RepairToolsPort confined to one disposable workspace copy."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.changed_files: list[str] = []

    def read_file(self, path: str) -> str:
        """Read a UTF-8 text file from within the workspace."""
        return safe_path(self.workspace, path).read_text(encoding="utf-8")

    def edit_file(self, path: str, content: str) -> None:
        """Write content to a workspace file and record the change once."""
        safe_path(self.workspace, path).write_text(content, encoding="utf-8")
        if path not in self.changed_files:
            self.changed_files.append(path)

    def run_tests(self) -> TestResult:
        """Delegate to the Docker-backed runner; never run fixture code on the host."""
        return runner.run_tests_in_docker(self.workspace)
