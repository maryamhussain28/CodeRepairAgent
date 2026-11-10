"""A scripted ChatClient: returns prepared replies in order, for repeatable tests."""


class ScriptedClient:
    """Answer-card model: each chat() call returns the next prepared reply."""

    def __init__(self, replies: list[str]):
        self._replies = list(replies)
        self._index = 0

    def chat(self, messages: list[dict]) -> str:
        """Return the next prepared reply, ignoring the message history."""
        if self._index >= len(self._replies):
            raise IndexError("ScriptedClient has no more prepared replies")
        reply = self._replies[self._index]
        self._index += 1
        return reply
