import os
import re
from cached_path import cached_path  # type: ignore
import numpy as np
import soundfile as sf  # type: ignore
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

default_voice_config = {
    "ref_audio_path": "/mnt/Daten/Datentausch/Redmi/Audiobooks/reference.mp3",
    "ref_text_input": "This link is first revealed when Roland meets Jake, a boy from the New York of 1977, at a desert waystation.",
    "speed_slider": 1.0,
}


class TTSBackendF5(TTSBackend):
    def __init__(self, env_name, temp_dir):
        self.env_name = env_name
        self.temp_dir = os.path.join(temp_dir, "f5")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.vocoder = self.load_vocoder()
        self.ema_model = self.load_model()

    def load_vocoder(self):
        vocoder_name = "vocos"
        vocoder_local_path = "../checkpoints/vocos-mel-24khz"
        with contextlib.redirect_stdout(None):
            return load_vocoder(
                vocoder_name=vocoder_name,
                is_local=False,
                local_path=vocoder_local_path,
            )

    def load_model(self):
        model_cls = DiT
        model_cfg = dict(
            dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4
        )
        ckpt_file = str(
            cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors")
        )
        with contextlib.redirect_stdout(None):
            return load_model(
                model_cls, model_cfg, ckpt_file, mel_spec_type="vocos", vocab_file=""
            )

    def cleanup(self):
        pass

    def synthesize_batch(self, text_items: list[dict]) -> list[np.ndarray]:
        numpy_waves = []

        loop_obj = tqdm(text_items, desc="Synthesizing")

        for text_item in loop_obj:
            text_data = text_item[0]
            voice_data = text_item[1]

            loop_obj.set_postfix_str(f"Synthesizing: {text_data['text']}")

            with contextlib.redirect_stdout(None):
                numpy_waves.append(
                    self.main_process(
                        voice_data["ref_audio_path"],
                        voice_data["ref_text_input"],
                        text_data["text"],
                        self.ema_model,
                        self.vocoder,
                        False,
                        voice_data.get("speed_slider", 1.0),
                        self.temp_dir,
                    )
                )

        return numpy_waves

    def main_process(
        self,
        ref_audio,
        ref_text,
        gen_text,
        ema_model,
        vocoder,
        remove_silence,
        speed,
        output_dir,
    ) -> np.ndarray:
        ref_audio, ref_text = preprocess_ref_audio_text(ref_audio, ref_text)

        generated_audio_segments = []
        reg1 = r"(?=\[\w+\])"
        chunks = re.split(reg1, gen_text)
        reg2 = r"\[(\w+)\]"
        for i, text in enumerate(chunks):
            if not text.strip():
                continue

            text = re.sub(reg2, "", text)
            gen_text_ = text.strip()

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
                temp_wave_path = os.path.join(output_dir, "temp.wav")
                sf.write(temp_wave_path, final_wave, final_sample_rate)
                remove_silence_for_generated_wav(temp_wave_path)
                final_wave, _ = sf.read(temp_wave_path)
                os.remove(temp_wave_path)

        if os.path.exists(ref_audio):
            os.remove(ref_audio)

        return final_wave
