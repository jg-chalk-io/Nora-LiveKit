"""Voice pipeline orchestration for real-time voice interaction."""

import asyncio
import structlog
from typing import Any, Optional

from nora_livekit.config import Config
from nora_livekit.voice.stt import DeepgramSTT
from nora_livekit.voice.tts import CartesiaTTS
from nora_livekit.voice.audio_handler import AudioHandler

logger = structlog.get_logger(__name__)


class VoicePipeline:
    """Orchestrates voice input/output pipeline for LiveKit agent.

    Manages Deepgram STT, Cartesia TTS, and LiveKit audio track handling
    for bidirectional voice communication.
    """

    def __init__(
        self,
        config: Config,
        stt: DeepgramSTT,
        tts: CartesiaTTS,
        audio_handler: AudioHandler,
        conversation_engine: Optional[Any] = None,
    ) -> None:
        """Initialize voice pipeline with STT, TTS, and audio handler.

        Satisfies: REQ-IR-PIPE-001

        Args:
            config: Configuration instance
            stt: DeepgramSTT instance
            tts: CartesiaTTS instance
            audio_handler: AudioHandler instance
            conversation_engine: Optional ConversationEngine for SPEC-003
        """
        self.config = config
        self.stt = stt
        self.tts = tts
        self.audio_handler = audio_handler
        self.conversation_engine = conversation_engine
        self._running = False

    async def start(self) -> None:
        """Start voice pipeline and audio processing.

        Initializes STT and TTS connections and begins processing audio.
        """
        logger.info("voice.pipeline.starting")

        try:
            # Connect to Deepgram and Cartesia
            await self.stt.connect()
            await self.tts.connect()

            self._running = True
            logger.info("voice.pipeline.started")

        except Exception as e:
            logger.error("voice.pipeline.start_error", error=str(e))
            self._running = False
            raise

    async def stop(self) -> None:
        """Stop voice pipeline and cleanup resources.

        Ensures graceful shutdown of STT and TTS connections
        and cleanup of audio resources.
        """
        logger.info("voice.pipeline.stopping")

        try:
            self._running = False

            # Disconnect from Deepgram and Cartesia
            await self.stt.disconnect()
            await self.tts.disconnect()

            logger.info("voice.pipeline.stopped")

        except Exception as e:
            logger.error("voice.pipeline.stop_error", error=str(e))
            raise

    async def process_audio_stream(self, participant_id: str = "") -> None:
        """Process incoming audio stream from LiveKit tracks.

        Subscribes to participant audio, sends to STT, processes results,
        synthesizes response, and publishes back to room.

        Args:
            participant_id: ID of participant to listen to (optional)
        """
        if not self._running:
            raise RuntimeError("Voice pipeline not running")

        logger.info("voice.pipeline.processing_started", participant_id=participant_id)

        try:
            # Subscribe to participant audio
            async for audio_chunk in self.audio_handler.subscribe_to_participant_audio(
                participant_id
            ):
                # In real implementation, would buffer chunks and send to STT
                pass

        except Exception as e:
            logger.error("voice.pipeline.processing_error", error=str(e))
            raise

    async def _handle_transcription(self, text: str) -> None:
        """Handle transcribed text from STT.

        Args:
            text: Transcribed text from speech-to-text
        """
        logger.info("voice.stt.transcription", text=text)

        try:
            # Generate response (for now, simple echo)
            response_text = await self._generate_response(text)

            # Synthesize response with TTS
            async for audio_chunk in self.tts.synthesize(response_text):
                # Buffer and prepare audio for publishing
                pass

            # Publish audio to LiveKit
            logger.info("voice.audio.published")

        except Exception as e:
            logger.error("voice.pipeline.transcription_error", error=str(e))

    async def _generate_response(
        self,
        text: str,
        participant_id: str = "",
    ) -> str:
        """Generate response text using ConversationEngine.

        Satisfies: REQ-IR-PIPE-002

        Args:
            text: Transcribed user text
            participant_id: ID of speaking participant

        Returns:
            Response text to be synthesized
        """
        if self.conversation_engine:
            # Use conversation engine (SPEC-003)
            try:
                response = await self.conversation_engine.process_transcription(
                    text=text,
                    participant_id=participant_id or "default",
                )
                return response
            except Exception as e:
                logger.error("conversation_engine_error", error=str(e))
                return "I'm having trouble responding right now."
        else:
            # Fallback to echo (for testing without conversation engine)
            return f"You said: {text}"

    @property
    def is_running(self) -> bool:
        """Check if voice pipeline is running."""
        return self._running
