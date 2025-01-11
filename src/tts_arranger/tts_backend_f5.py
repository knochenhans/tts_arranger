import os
import re
from typing import Any, Dict, List, Callable, Optional
from cached_path import cached_path  # type: ignore
import numpy as np
from platformdirs import user_data_dir
import soundfile as sf  # type: ignore

from tts_arranger.functions import load_default_voices  # type: ignore
from .tts_backend import TTSBackend
from f5_tts.infer.utils_infer import (  # type: ignore
    target_rms,
    cross_fade_duration,
    nfe_step,
    cfg_strength,
    sway_sampling_coef,
    fix_duration,
    infer_process,
    load_model,
    load_vocoder,
    preprocess_ref_audio_text,
    remove_silence_for_generated_wav,
)
from f5_tts.model import DiT  # type: ignore
import contextlib
from tqdm import tqdm  # type: ignore
from loguru import logger  # type: ignore
import random

TextItem = Dict[str, str | float]


class TTSBackendF5(TTSBackend):
    def __init__(
        self,
        env_name: str,
        temp_dir: str,
        backend_config: Dict[str, Any],
        progress_callback: Optional[Callable[[int], None]] = None,
    ):
        self.env_name: str = env_name
        self.temp_dir: str = os.path.join(temp_dir, "f5")
        self.backend_config: Dict[str, Any] = backend_config
        self.progress_callback: Optional[Callable[[int], None]] = progress_callback

        os.makedirs(self.temp_dir, exist_ok=True)

        self.vocoder: Any = self.load_vocoder()
        self.ema_model: Any = self.load_model()

        self.voices: Dict[str, Dict[str, Any]] = load_default_voices()

        logger.info("F5 TTS backend initialized")

    def load_vocoder(self) -> Any:
        vocoder_name: str = "vocos"
        vocoder_local_path: str = "../checkpoints/vocos-mel-24khz"
        with contextlib.redirect_stdout(None):
            return load_vocoder(
                vocoder_name=vocoder_name,
                is_local=False,
                local_path=vocoder_local_path,
            )

    def load_model(self) -> Any:
        model_cls = DiT
        model_cfg: Dict[str, Any] = dict(
            dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4
        )
        ckpt_file: str = str(
            cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors")
        )
        with contextlib.redirect_stdout(None):
            return load_model(
                model_cls, model_cfg, ckpt_file, mel_spec_type="vocos", vocab_file=""
            )

    def cleanup(self) -> None:
        pass

    def synthesize_batch(self, text_items: List[TextItem]) -> List[np.ndarray]:
        numpy_waves: List[np.ndarray] = []

        loop_obj = tqdm(text_items, desc="Synthesizing")

        for i, text_item in enumerate(loop_obj):
            # If no text is found, but min_length is found, insert a pause
            if (
                not text_item.get("text", "")
                and float(text_item.get("min_length", 0)) > 0
            ):
                numpy_waves.append(
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

            speaker_id: str = str(text_item.get("speaker_id", ""))

            if speaker_id is None:
                raise ValueError(
                    f"Speaker ID {speaker_id} not found for text item {text_item}"
                )

            speaker_id_mapping: Dict[str, str] = self.backend_config.get(
                "speaker_id_mapping", {}
            )

            voice_ids = speaker_id_mapping.get(speaker_id, "")

            if not voice_ids:
                raise ValueError(f"No voice IDs found for speaker {speaker_id}")
            
            voice_id = voice_ids[0]

            # voice_ids is a list of voice id, pick a random one
            voice_id = random.choice(voice_ids)

            # if voice_id == "":
            #     raise ValueError(
            #         f"Voice ID {voice_id} not found for mapped speaker {speaker_id}"
            #     )

            voice: Dict[str, Any] = self.voices.get(voice_id, {})

            if not voice:
                raise ValueError(f"Voice {voice_id} not found for speaker {speaker_id}")
            
            # logger.debug(f"Using voice {voice_id} for speaker {speaker_id} - text: {text}")

            max_speed: float = self.voices[voice_id].get("speed_slider", 1.0)

            with contextlib.redirect_stdout(None):
                numpy_waves.append(
                    self.main_process(
                        voice["ref_audio_path"],
                        voice["ref_text_input"],
                        text,
                        self.ema_model,
                        self.vocoder,
                        False,
                        min(float(text_item.get("speed_slider", 1.0)), max_speed),
                        self.temp_dir,
                    )
                )

            if self.progress_callback:
                self.progress_callback(i)

        return numpy_waves

    def main_process(
        self,
        ref_audio: str,
        ref_text: str,
        gen_text: str,
        ema_model: Any,
        vocoder: Any,
        remove_silence: bool,
        speed: float,
        output_dir: str,
    ) -> np.ndarray:
        ref_audio, ref_text = preprocess_ref_audio_text(ref_audio, ref_text)

        generated_audio_segments: List[np.ndarray] = []
        reg1: str = r"(?=\[\w+\])"
        chunks: List[str] = re.split(reg1, gen_text)
        reg2: str = r"\[(\w+)\]"
        for i, text in enumerate(chunks):
            if not text.strip():
                continue

            text = re.sub(reg2, "", text)
            gen_text_: str = text.strip()

            audio_segment, final_sample_rate, _ = infer_process(
                ref_audio,
                ref_text,
                gen_text_,
                ema_model,
                vocoder,
                mel_spec_type="vocos",
                show_info=lambda *args, **kwargs: None,  # Suppress output
                target_rms=target_rms,
                cross_fade_duration=cross_fade_duration,
                nfe_step=nfe_step,
                cfg_strength=cfg_strength,
                sway_sampling_coef=sway_sampling_coef,
                speed=speed,
                fix_duration=fix_duration,
            )
            generated_audio_segments.append(audio_segment)

        # Create empty numpy array
        final_wave: np.ndarray = np.array([], dtype=np.float32)

        if generated_audio_segments:
            final_wave = np.concatenate(generated_audio_segments)

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            if remove_silence:
                temp_wave_path: str = os.path.join(output_dir, "temp.wav")
                sf.write(temp_wave_path, final_wave, final_sample_rate)
                remove_silence_for_generated_wav(temp_wave_path)
                final_wave, _ = sf.read(temp_wave_path)
                os.remove(temp_wave_path)

        if os.path.exists(ref_audio):
            os.remove(ref_audio)

        return final_wave
