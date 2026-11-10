"""Gradio presentation layer: shows the existing RepairService's result.

This module makes no repair decisions, builds no prompts, and never calls
Docker directly; it only displays what RepairService/RepairAgent already did.
"""

import shutil
import tempfile
from pathlib import Path

import gradio as gr

from bootstrap import build_repair_service

CASES = ["arithmetic", "balanced_brackets", "median", "multi_function", "unique_words"]


def _format_trace(trace: list[dict]) -> str:
    return "\n".join(f"[{entry['event']}] {entry}" for entry in trace)


def _format_changed_files(result) -> str:
    if not result.changed_files:
        return "(no files changed)"
    workspace = Path(result.workspace)
    sections = []
    for relative_path in result.changed_files:
        full_path = workspace / relative_path
        content = full_path.read_text(encoding="utf-8") if full_path.exists() else "(file not found)"
        sections.append(f"--- {relative_path} ---\n{content}")
    return "\n\n".join(sections)


def _zip_workspace(result) -> str | None:
    """Package the disposable repaired workspace as a downloadable zip."""
    workspace = Path(result.workspace) if result.workspace else None
    if not workspace or not workspace.is_dir():
        return None
    archive_base = Path(tempfile.mkdtemp()) / workspace.name
    return shutil.make_archive(str(archive_base), "zip", root_dir=workspace)


def run_selected_repair(case_name: str):
    """Run the existing RepairService for one of the five supplied cases."""
    service = build_repair_service("scripted")
    result = service.repair(f"evals/{case_name}")

    status = "PASSED" if result.passed else "FAILED"
    test_output = result.last_test_result.output if result.last_test_result else "(no test result)"
    return (
        _format_trace(result.trace),
        _format_changed_files(result),
        test_output,
        status,
        _zip_workspace(result),
    )


def create_demo() -> gr.Blocks:
    """Build the Gradio page: pick a supplied case, run the repair service, show the result."""
    with gr.Blocks(title="Python Repair Agent") as demo:
        gr.Markdown("# Python Repair Agent")
        case_dropdown = gr.Dropdown(choices=CASES, value=CASES[0], label="Evaluation project")
        start_button = gr.Button("Run repair")

        status_box = gr.Textbox(label="Result", interactive=False)
        trace_box = gr.Textbox(label="Trace", lines=12, interactive=False)
        changed_box = gr.Textbox(label="Changed files", lines=12, interactive=False)
        test_output_box = gr.Textbox(label="Final test output", lines=8, interactive=False)
        download_file = gr.File(label="Download repaired workspace (zip)")

        start_button.click(
            fn=run_selected_repair,
            inputs=case_dropdown,
            outputs=[trace_box, changed_box, test_output_box, status_box, download_file],
        )

    return demo
