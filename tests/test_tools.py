"""Unit tests for the safe workspace tools."""

from unittest.mock import patch

import pytest

from adapters.sandbox.repair_tools import RepairTools, safe_path
from core.models import TestResult


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "sample.py").write_text("value = 1\n", encoding="utf-8")
    return tmp_path


def test_safe_path_allows_relative_path_inside_workspace(workspace):
    assert safe_path(workspace, "sample.py") == (workspace / "sample.py").resolve()


def test_safe_path_rejects_absolute_path(workspace):
    with pytest.raises(ValueError):
        safe_path(workspace, "/etc/passwd")


def test_safe_path_rejects_parent_traversal(workspace):
    with pytest.raises(ValueError):
        safe_path(workspace, "../secret.txt")


def test_read_file_returns_workspace_contents(workspace):
    tools = RepairTools(workspace)
    assert tools.read_file("sample.py") == "value = 1\n"


def test_edit_file_saves_and_records_change_once(workspace):
    tools = RepairTools(workspace)
    tools.edit_file("sample.py", "value = 2\n")
    tools.edit_file("sample.py", "value = 3\n")
    assert (workspace / "sample.py").read_text(encoding="utf-8") == "value = 3\n"
    assert tools.changed_files == ["sample.py"]


def test_run_tests_delegates_to_docker_runner(workspace):
    expected = TestResult(passed=True, output="1 passed", returncode=0)
    tools = RepairTools(workspace)
    with patch(
        "adapters.sandbox.repair_tools.runner.run_tests_in_docker",
        return_value=expected,
    ) as mocked:
        result = tools.run_tests()
    mocked.assert_called_once_with(workspace)
    assert result is expected
