"""Mock LiveKit components for testing."""


class MockVoiceAssistant:
    """Mock LiveKit VoiceAssistant for testing."""

    def __init__(self):
        """Initialize mock assistant."""
        self.messages = []
        self.is_connected = False
        self.callbacks = {}

    async def connect(self, url: str, token: str) -> None:
        """Mock connection to LiveKit room.

        Args:
            url: Room URL
            token: Room token
        """
        self.is_connected = True

    async def disconnect(self) -> None:
        """Mock disconnection from LiveKit room."""
        self.is_connected = False

    async def send_message(self, text: str) -> None:
        """Mock sending a message.

        Args:
            text: Message text
        """
        self.messages.append({"role": "assistant", "content": text})

    def on_message(self, callback) -> None:
        """Register message callback.

        Args:
            callback: Callback function
        """
        self.callbacks["on_message"] = callback

    def on_transfer(self, callback) -> None:
        """Register transfer callback.

        Args:
            callback: Callback function
        """
        self.callbacks["on_transfer"] = callback

    def on_end(self, callback) -> None:
        """Register end callback.

        Args:
            callback: Callback function
        """
        self.callbacks["on_end"] = callback
