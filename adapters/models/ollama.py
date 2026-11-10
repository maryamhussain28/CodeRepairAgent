"""Sends prepared messages to a local Ollama server and returns the reply text.

This is only a transport: it requests JSON-formatted output from Ollama as a
hint, but it never parses or validates the reply itself. RepairAgent still
validates every reply against the three allowed actions.
"""

import json
import urllib.request

DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_BASE_URL = "http://localhost:11434"
REQUEST_TIMEOUT_SECONDS = 120


class OllamaClient:
    """ChatClient backed by a local Ollama server."""

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.0, base_url: str = DEFAULT_BASE_URL):
        self.model = model
        self.temperature = temperature
        self.base_url = base_url

    def chat(self, messages: list[dict]) -> str:
        """Send the message history to Ollama's chat endpoint and return the reply text."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read())
        return body["message"]["content"]
