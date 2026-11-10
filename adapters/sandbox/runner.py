"""Creates a disposable workspace copy of an eval case and tests it in Docker."""

import shutil
import subprocess
import uuid
from pathlib import Path

from core.models import TestResult

# Under the home directory, not the system temp dir: Docker Desktop shares
# macOS's /var/folders with its VM, but Colima, Rancher Desktop, and Podman
# only share the home directory. A mount of an unshared path is empty inside
# the container.
WORKSPACE_ROOT = Path.home() / ".cache" / "coding-agent-lab"
IMAGE_NAME = "coding-agent-lab-runner"


def create_workspace(case_dir: Path) -> Path:
    """Copy one evals/<case> directory into a new disposable workspace."""
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    workspace = WORKSPACE_ROOT / f"{case_dir.name}-{uuid.uuid4().hex[:8]}"
    shutil.copytree(case_dir, workspace)
    return workspace


def run_tests_in_docker(workspace: Path) -> TestResult:
    """Run pytest against the workspace copy in a short-lived, network-disabled container."""
    process = subprocess.run(
        [
            "docker", "run", "--rm",
            "--network", "none",
            "-v", f"{workspace}:/workspace:ro",
            IMAGE_NAME,
        ],
        capture_output=True,
        text=True,
    )
    output = process.stdout + process.stderr
    return TestResult(passed=process.returncode == 0, output=output, returncode=process.returncode)
