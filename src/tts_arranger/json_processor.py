import io
import json
import os
import tempfile
import wave
from pathlib import Path

import ffmpeg  # type: ignore
import numpy as np
import scipy  # type: ignore
from piper import PiperVoice  # type: ignore
from piper.download import find_voice, get_voices  # type: ignore

from tts_arranger.utils.log import LOG_TYPE, log  # type: ignore


class JSON_Processor:
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.download_dir = "/usr/share/piper-voices/"
        self.sample_rate = 22050

    def synthesize_project(self) -> None:
        with open(self.json_path, "r") as file:
            json_data = json.load(file)

        if "chapters" in json_data:
            chapters = json_data["chapters"]

        model_ids: dict[str, list[str]] = {}

        for chapter in chapters:
            if "items" in chapter:
                items = chapter["items"]

                # Collect model information
                for item in items:
                    if "backend_properties" in item:
                        backend_properties = item["backend_properties"]
                        if "backend" in backend_properties:
                            if backend_properties["backend"] not in model_ids:
                                model_ids[backend_properties["backend"]] = []
                        if "model" in backend_properties:
                            if (
                                backend_properties["model"]
                                not in model_ids[backend_properties["backend"]]
                            ):
                                model_ids[backend_properties["backend"]].append(
                                    backend_properties["model"]
                                )

        # Load models

        voices: dict[str, PiperVoice] = {}

        for backend in model_ids:
            if backend == "piper":
                for model_id in model_ids[backend]:
                    # Load voice info
                    voices_info = get_voices(self.download_dir, update_voices=False)

                    # ensure_voice_exists(model, [download_dir], download_dir, voices_info)

                    file = (
                        self.download_dir
                        + list(voices_info[model_id]["files"].keys())[0]
                    )

                    dir = Path(str(file)).parent
                    model_id_path, config = find_voice(model_id, [dir])

                    # model_id_str = str(model_id)

                    voices[model_id] = PiperVoice.load(
                        model_id_path, config_path=config, use_cuda=False
                    )

                    print(f"Loaded voice {model_id} from {config}")

                    # Load config JSON
                    with open(config, "r", encoding="utf-8") as config_file:
                        config_dict = json.load(config_file)

                        # Set the sample rate to the highest value found in the used models
                        sample_rate = config_dict["audio"]["sample_rate"]
                        if sample_rate > self.sample_rate:
                            self.sample_rate = sample_rate

                    # voice_speakers = list(config_dict["speaker_id_map"])

        numpy_segments = np.array([0], dtype=np.float32)

        # Get count of all items in all chapters
        total_items = 0

        for chapter in chapters:
            if "items" in chapter:
                total_items += len(chapter["items"])

        for c, chapter in enumerate(chapters):
            if "items" in chapter:
                items = chapter["items"]

                for i, item in enumerate(items):
                    log(
                        LOG_TYPE.INFO,
                        f"Processing item {i+1} of {len(items)} in chapter {c+1} of {len(chapters)}",
                    )

                    if (
                        "text" in item
                        and item["text"] is not None
                        and item["text"] != ""
                    ):
                        speaker_id = None

                        synthesize_args = {
                            "speaker_id": speaker_id,
                            "length_scale": None,
                            "noise_scale": None,
                            "noise_w": None,
                            "sentence_silence": 0.5,
                        }

                        # Quick and dirty way to get this running for now
                        wave_io = io.BytesIO()
                        with wave.open(wave_io, "wb") as wav_file:
                            voices[item["backend_properties"]["model"]].synthesize(
                                item["text"], wav_file, **synthesize_args
                            )
                        wave_io.seek(0)
                        # Open the BytesIO object as a wave file again to read the frames
                        with wave.open(wave_io, "rb") as wav_file:
                            frames = wav_file.readframes(wav_file.getnframes())

                        # Convert the bytes to a numpy float32 array
                        numpy_wav = np.frombuffer(frames, dtype=np.int16).astype(
                            np.float32
                        )

                        # Normalize the values to the range [-1, 1]
                        numpy_wav /= np.iinfo(np.int16).max
                        numpy_segments = np.concatenate((numpy_segments, numpy_wav))

        if numpy_segments.size > 1:
            self._write(numpy_segments, "/tmp/output")

    def get_model_paths(self):
        return self.download_dir

    def _write(self, numpy_segment: np.ndarray, output_filename: str) -> None:
        """
        Compress, convert and write numpy array as a given output file path and name

        :param segment: numpy array to be written
        :type segment: np.ndarray

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """
        # Set default format to mp3
        output_format = os.path.splitext(output_filename)[1][1:] or "mp3"

        folder = os.path.dirname(os.path.abspath(output_filename))

        os.makedirs(folder, exist_ok=True)

        # Ensure output file name has a file extension
        output_filename = os.path.splitext(output_filename)[0] + "." + output_format

        log(LOG_TYPE.INFO, f"Compressing, converting and saving as {output_filename}.")

        output_args = {}

        if output_format == "mp3":
            output_args["audio_bitrate"] = "320k"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "temp")
            scipy.io.wavfile.write(temp_path, self.sample_rate, numpy_segment)

            # comp_expansion = 12.5
            # comp_raise = 0.0001

            # Convert to target format
            (
                ffmpeg.input(temp_path)
                # .filter("speechnorm", e=f"{comp_expansion}", r=f"{comp_raise}", l=1)
                .output(output_filename, **output_args, loglevel="error").run(
                    overwrite_output=True
                )
            )


# json_processor = JSON_Processor("src/tts_arranger/data/test.json")
json_processor = JSON_Processor("/tmp/project.json")
json_processor.synthesize_project()

numpy_segments = np.array([0], dtype=np.float32)
