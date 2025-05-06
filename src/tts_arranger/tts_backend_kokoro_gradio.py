import io
import os
import random
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import soundfile as sf  # type: ignore
from gradio_client import Client  # type: ignore
from loguru import logger
from tqdm import tqdm

from tts_arranger.tts_backend import TTSBackend

TextItem = Dict[str, Union[str, float]]


class TTSBackendKokoroGradio(TTSBackend):
    def __init__(
        self,
        env_name: str,
        temp_dir: str,
        backend_config: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ):
        self.env_name: str = env_name
        self.temp_dir: str = os.path.join(temp_dir, "kokoro_tts")
        self.backend_config: Dict[str, Any] = backend_config
        self.progress_callback: Optional[Callable[[int], None]] = progress_callback

        os.makedirs(self.temp_dir, exist_ok=True)

        self.client = Client("http://192.168.178.38:42003/")
        self.voices = {
            "0": "🇺🇸 🚹 Echo",
            "1": "🇬🇧 🚹 George",
            "2": "🇬🇧 🚹 Lewis",
            "3": "🇺🇸 🚺 Heart ❤️",
            "4": "🇺🇸 🚺 Aoede",
            "5": "🇺🇸 🚺 Kore",
            "6": "🇺🇸 🚺 Sarah",
            "7": "🇺🇸 🚺 Alloy",
            "8": "🇺🇸 🚹 Fenrir",
            "9": "🇺🇸 🚹 Liam",
            "10": "🇬🇧 🚺 Emma",
            "11": "🇬🇧 🚺 Isabelle",
            "12": "🇬🇧 🚺 Lily",
            "13": "🇬🇧 🚹 Fable",
            "normal": "🇺🇸 🚹 Echo",
            "highlight": "🇬🇧 🚹 George",
        }

        logger.info("Kokoro TTS backend initialized")

    def cleanup(self) -> None:
        pass

    async def synthesize_batch(self, text_items: List[TextItem]) -> None:
        self.results = []

        loop_obj = tqdm(text_items, desc="Synthesizing")

        for i, text_item in enumerate(loop_obj):
            text: str = str(text_item.get("text", ""))
            if not text.strip():
                self.results.append(np.zeros(0))  # Append empty result for empty text
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

            voice = self.voices.get(
                speaker_id, "🇬🇧 🚹 George"
            )  # Fallback to default voice if ID is invalid

            speed = text_item.get("speed", 0.9)  # Default speed

            retries = 3
            for attempt in range(retries):
                try:
                    # Use the Kokoro TTS API to generate audio
                    result = self.client.predict(
                        text=text,
                        voice=voice,
                        speed=speed,
                        api_name="/generate_first",
                    )

                    # Read the audio data directly into a numpy array
                    audio_bytes = open(result[0], "rb")
                    audio_data, _ = sf.read(audio_bytes)
                    self.results.append(audio_data)

                    # Remove the temporary file if it exists
                    os.remove(result[0])

                    # Remove the parent folder if it is empty
                    parent_folder = os.path.dirname(result[0])
                    if os.path.exists(parent_folder) and not os.listdir(parent_folder):
                        os.rmdir(parent_folder)
                    break

                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {e} for text: {text}")
                    if attempt == retries - 1:
                        self.results.append(
                            np.zeros(0)
                        )  # Append empty result on final failure

            if self.progress_callback:
                self.progress_callback(i)
