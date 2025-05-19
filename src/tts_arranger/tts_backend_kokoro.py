import os
import random
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import torch
from kokoro import KPipeline  # type: ignore
from loguru import logger  # type: ignore
from torch import FloatTensor
from tqdm import tqdm  # type: ignore

from .tts_backend import TTSBackend

TextItem = Dict[str, str | float]


class TTSBackendKokoro(TTSBackend):
    def __init__(
        self,
        env_name: str,
        temp_dir: str,
        backend_config: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ):
        super().__init__()

        self.env_name: str = env_name
        self.temp_dir: str = os.path.join(temp_dir, "kokoro_tts")
        self.backend_config: Dict[str, Any] = backend_config
        self.progress_callback: Optional[Callable[[int], None]] = progress_callback
        self.pack: Optional[Any] = None

        os.makedirs(self.temp_dir, exist_ok=True)

        # Initialize Kokoro TTS pipeline
        self.pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

        # Define available voices as a simple list
        self.voices: List[str] = [
            "af_heart",
            "af_alloy",
            "af_aoede",
            "af_bella",
            "af_jessica",
            "af_kore",
            "af_nicole",
            "af_nova",
            "af_river",
            "af_sarah",
            "af_sky",
            "am_adam",
            "am_echo",
            "am_eric",
            "am_fenrir",
            "am_liam",
            "am_michael",
            "am_onyx",
            "am_puck",
            "am_santa",
            "bf_alice",
            "bf_emma",
            "bf_isabella",
            "bf_lily",
            "bm_daniel",
            "bm_fable",
            "bm_george",
            "bm_lewis",
        ]

        logger.info("Kokoro TTS backend initialized")

    def cleanup(self) -> None:
        pass

    async def synthesize_batch(self, text_items: List[TextItem]) -> None:
        self.results = []
        current_voice_id = None

        loop_obj = tqdm(text_items, desc="Synthesizing")

        voice = None

        for i, text_item in enumerate(loop_obj):
            text: str = str(text_item.get("text", ""))
            if not text.strip():
                self.results.append(np.zeros(0))  # Append empty result for empty text
                continue

            # Get speaker ID from text item
            speaker_id: str = str(text_item.get("speaker_id", ""))
            if not speaker_id:
                logger.error(
                    f"Speaker ID {speaker_id} not found for text item {text_item}, using empty ID"
                )

            # Get speaker-to-voice mapping from backend config
            speaker_id_mapping: Dict[str, List[str]] = self.backend_config.get(
                "speaker_id_mapping", {}
            )
            voice_ids = speaker_id_mapping.get(speaker_id, [])
            voice_id = voice_ids[0]
            split_voice_id = voice_id.split(" ")

            try:
                # Load the voice only if it has changed
                if voice_id != current_voice_id or voice is None:
                    if len(split_voice_id) > 1:
                        voice = self.get_combined_voice(voice_id)
                    else:
                        # Select a voice ID
                        if not voice_ids:
                            voice = self.voices[0]  # Default to the first voice
                            logger.warning(
                                f"No voice IDs found for speaker {speaker_id}, using default voice {voice}"
                            )
                        else:
                            voice = random.choice(voice_ids)

                            self.pack = self.pipeline.load_single_voice(voice)

                    current_voice_id = voice_id

                # Generate audio using Kokoro TTS pipeline
                generator = self.pipeline(text, voice)  # type: ignore
                audio_data = []

                for _, _, audio in generator:
                    if isinstance(audio, FloatTensor):
                        audio = audio.numpy()
                    if isinstance(audio, (list, np.ndarray)):
                        audio_data.extend(audio)
                    else:
                        logger.warning(f"Unexpected audio type: {type(audio)}")

                # Convert audio data to numpy array
                audio_array = np.array(audio_data, dtype=np.float32)

                # Change volume by multiplying with a factor (e.g., 1.5 for 50% increase)
                volume_factor = self.voice_config.get(voice_id, {}).get(
                    "volume_factor", 1.0
                )
                audio_array = np.clip(audio_array * volume_factor, -1.0, 1.0)

                self.results.append(audio_array)

            except Exception as e:
                logger.error(f"Error synthesizing text: {e} for text: {text}")
                self.results.append(np.zeros(0))  # Append empty result on failure

            finally:
                # Ensure generator is fully consumed or closed
                if "generator" in locals():
                    del generator  # Explicitly delete generator to release resources

            if self.progress_callback:
                self.progress_callback(i)

    def parse_voice_formula(self, formula: str) -> Optional[torch.Tensor]:
        if not formula.strip():
            raise ValueError("Empty voice formula")

        # Initialize the weighted sum
        weighted_sum = None

        # Split the formula into terms
        terms = formula.split("+")

        base_path = "/mnt/Daten/Downloads/Kokoro-82M/voices/"

        voices = {}
        for voice_file in self.voices:
            voice_name = os.path.splitext(voice_file)[0]
            voices[voice_name] = torch.load(
                os.path.join(base_path, voice_file + ".pt"), weights_only=True
            )

        for term in terms:
            # Parse each term (format: "0.333 * voice_name")
            weight, voice_name = term.strip().split("*")
            weight = float(weight.strip())
            voice_name = voice_name.strip()

            # Get the voice tensor
            if voice_name not in self.voices:
                raise ValueError(f"Unknown voice: {voice_name}")

            voice_tensor = voices[voice_name]

            # Add to weighted sum
            if weighted_sum is None:
                weighted_sum = weight * voice_tensor
            else:
                weighted_sum += weight * voice_tensor

        return weighted_sum

    def get_combined_voice(self, formula: str) -> Optional[torch.Tensor]:
        try:
            # Parse the formula and get the combined voice tensor
            combined_voice = self.parse_voice_formula(formula)
            return combined_voice
        except Exception as e:
            logger.error(f"Failed to create combined voice: {str(e)}")
            raise
