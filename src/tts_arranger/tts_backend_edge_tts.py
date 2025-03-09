import io
import os
import random
from typing import Any, Dict, List, Callable, Optional
import numpy as np
from platformdirs import user_data_dir
import soundfile as sf  # type: ignore
import time
import asyncio

from tts_arranger.functions import load_default_voices  # type: ignore
from .tts_backend import TTSBackend
import edge_tts  # type: ignore
from edge_tts.exceptions import (
    NoAudioReceived,
    UnexpectedResponse,
    UnknownResponse,
    WebSocketError,
)
from tqdm import tqdm
from loguru import logger
import unicodedata

TextItem = Dict[str, str | float]


class TTSBackendEdge(TTSBackend):
    def __init__(
        self,
        env_name: str,
        temp_dir: str,
        backend_config: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ):
        self.env_name: str = env_name
        self.temp_dir: str = os.path.join(temp_dir, "edge_tts")
        self.backend_config: Dict[str, Any] = backend_config
        self.progress_callback: Optional[Callable[[int], None]] = progress_callback

        os.makedirs(self.temp_dir, exist_ok=True)

        self.voices: Dict[str, Dict[str, Any]] = load_default_voices(backend="edge-tts")

        logger.info("Edge TTS backend initialized")

    def cleanup(self) -> None:
        pass

    async def synthesize_batch(self, text_items: List[TextItem]) -> None:
        self.results = []

        loop_obj = tqdm(text_items, desc="Synthesizing")

        for i, text_item in enumerate(loop_obj):
            if (
                not text_item.get("text", "")
                and float(text_item.get("min_length", 0)) > 0
            ):
                self.results.append(
                    np.zeros(
                        int(
                            text_item["min_length"]
                            * self.backend_config.get("sample_rate", 24000)
                            / 1000
                        )
                    )
                )
                continue

            text: str = str(text_item.get("text", ""))

            if text.strip() == "":
                continue

            if all(unicodedata.category(char).startswith("P") for char in text.strip()):
                continue

            if not any(
                unicodedata.category(char).startswith(("L", "N"))
                for char in text.strip()
            ):
                continue

            speaker_id: str = str(text_item.get("speaker_id", ""))

            if speaker_id is None:
                logger.error(
                    f"Speaker ID {speaker_id} not found for text item {text_item}, using empty id"
                )

            speaker_id_mapping: Dict[str, str] = self.backend_config.get(
                "speaker_id_mapping", {}
            )

            voice_ids = speaker_id_mapping.get(speaker_id, "")

            if not voice_ids:
                voice_id = list(self.voices.keys())[0]
                logger.warning(
                    f"No voice IDs found for speaker {speaker_id}, using {voice_id} instead"
                )
            else:
                voice_id = random.choice(voice_ids)

            audio_bytes = io.BytesIO()

            # Adjust rate dynamically between 0% and -20% based on item length
            text_length = len(text)

            # rate_str = "-0%"

            # if text_length < 100:
            #     rate = round((25 / 99 * text_length - 2525 / 99))

            #     if rate != 0:
            #         rate_str = f"{rate}%"
            #         logger.debug(f"Adjusting rate to {rate_str} for text: {text}")

            for attempt in range(3):  # Try up to 3 times
                try:
                    # communicate = edge_tts.Communicate(text, voice_id, rate=rate_str, connect_timeout=30, receive_timeout=300)
                    communicate = edge_tts.Communicate(text, voice_id, connect_timeout=30, receive_timeout=300)
                    start_time = time.time()
                    async for chunk in communicate.stream():
                        if time.time() - start_time > 600:  # 10 minutes
                            logger.error(
                                f"Stream sync taking too long for text item: {text_item}"
                            )
                            raise TimeoutError("Stream sync exceeded 10 minutes")
                        if chunk["type"] == "audio":
                            if "data" in chunk:
                                audio_bytes.write(chunk["data"])
                    break  # Exit loop if successful
                except (
                    NoAudioReceived,
                    UnexpectedResponse,
                    UnknownResponse,
                    WebSocketError,
                ) as e:
                    logger.error(f"{type(e).__name__} for text: {text}")
                    if attempt < 2:
                        logger.info("Retrying in 60 seconds...")
                        await asyncio.sleep(60)
                    else:
                        logger.error(
                            f"All attempts to synthesize text failed due to {type(e).__name__}. Exiting."
                        )
                        raise SystemExit(e)
                except Exception as e:
                    logger.error(f"Error synthesizing text: {e} for text: {text}")
                    if attempt < 2:  # Wait only if it's not the last attempt
                        logger.info("Retrying in 60 seconds...")
                        await asyncio.sleep(60)
                    else:
                        logger.error("All attempts to synthesize text failed. Exiting.")
                        raise SystemExit(e)

            audio_bytes.seek(0)
            audio_data, _ = sf.read(io.BytesIO(audio_bytes.getvalue()))
            self.results.append(audio_data)

            if self.progress_callback:
                self.progress_callback(i)
