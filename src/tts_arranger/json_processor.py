import base64
from datetime import date
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Callable


from loguru import logger

import ffmpeg  # type: ignore
import numpy as np
import scipy  # type: ignore

from tts_arranger.functions import load_default_config
from tts_arranger.tts_backend import TTSBackend
from tts_arranger.tts_preprocessor import TTS_Preprocessor  # type: ignore

from .items.tts_project import TTS_Project  # type: ignore

from .tts_backend_f5 import TTSBackendF5
from .ffmpeg_processor import FFmpegProcessor

TextItem = Dict[str, str | float]


class JSON_Processor:
    def __init__(
        self,
        base_path: str,
        output_format: str = "m4b",
        backend_config: Optional[Dict[str, Any]] = None,
        speaker_id_mapping: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, int, int, int], None]] = None,
    ) -> None:
        self.NANOSECONDS_IN_ONE_SECOND = 1e9

        self.temp_files: List[Tuple[str, str]] = []
        self.temp_dir = "/tmp"
        self.chapter_times: List[Tuple[float, float]] = []
        self.item_data: List[Tuple[float, str]] = []
        self.project_path = base_path
        self.source_path = os.path.dirname(os.path.abspath(__file__))
        self.output_format = output_format
        self.backend: Optional[TTSBackend] = None
        self.progress_callback: Optional[Callable[[int, int, int, int], None]] = (
            progress_callback
        )

        if backend_config:
            self.backend_config = backend_config
        else:
            self.backend_config = load_default_config()

        if speaker_id_mapping:
            self.backend_config["speaker_id_mapping"] = speaker_id_mapping

        self.sample_rate = self.backend_config.get("sample_rate", 22050)

        self.current_item_count = 0
        self.current_chapter_count = 0
        self.current_chapter_idx = 0

    def load_json(self, json_path: str) -> Dict[str, Any]:
        # Update source path with absolute json path without filename
        self.source_path = os.path.dirname(os.path.abspath(json_path))

        with open(json_path, "r") as file:
            json_data = json.load(file)

        return json_data

    def get_chapters(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return json_data.get("chapters", [])

    def on_progress(self, current_item_idx: int) -> None:
        if self.progress_callback:
            self.progress_callback(
                current_item_idx,
                self.current_item_count,
                self.current_chapter_idx,
                self.current_chapter_count,
            )

    def synthesize_chapters(
        self,
        chapters: List[Dict[str, Any]],
        temp_dir: str = "/tmp",
        detailed: bool = False,
    ) -> None:
        self.temp_dir = temp_dir
        temp_format = "wav"
        cumulative_time: float = 0
        self.item_data.append((0, ""))

        self.current_chapter_count = len(chapters)
        for c, chapter in enumerate(chapters):
            self.current_chapter_idx = c

            logger.info(
                f"Processing chapter {c+1} of {len(chapters)}: {chapter.get('title', 'Chapter')}"
            )
            filename = os.path.join(temp_dir, f"tts_part_{c}.{temp_format}")
            items: List[TextItem] = chapter.get("items", [])

            self.backend = TTSBackendF5(
                "f5-tts", self.temp_dir, self.backend_config, self.on_progress
            )

            items_to_process: List[TextItem] = []
            for i, item in enumerate(items):
                text = ""

                if "text" in item:
                    text = str(item.get("text", ""))

                    if not isinstance(text, str):
                        continue
                else:
                    if "min_length" in item:
                        items_to_process.append(item)
                    else:
                        continue

                if not text.strip():
                    continue

                sentences = re.split(r"(?<=[.!?]) +|\n", text.strip())
                # speaker_id_mapping = deepcopy(self.backend_data["speaker_id_mapping"])
                # speaker_id = item.get("speaker_id", None)

                # if speaker_id in speaker_id_mapping:
                #     voice_id = speaker_id_mapping[speaker_id]
                # else:
                #     voice_id = list(speaker_id_mapping.values())[0]

                sentence_data, synthesize_splitted = self._split_sentences_by_speed(
                    sentences
                )

                if synthesize_splitted:
                    for i, sentence in sentence_data.items():
                        item = {
                            "text": sentence["sentence"],
                            "min_length": 0,
                            "speaker_id": item["speaker_id"],
                            "speed_slider": sentence["speed_slider"],
                        }
                        # speaker_id_mapping_copy = deepcopy(speaker_id_mapping)
                        # voice_id = speaker_id_mapping_copy.get(speaker_id, None)

                        items_to_process.append(item)
                else:
                    item = {
                        "text": text,
                        "min_length": item.get("min_length", 0),
                        "speaker_id": item["speaker_id"],
                    }

                    items_to_process.append(item)

            temp_files, segment_lengths = self.process_items(items_to_process)

            input_files = [ffmpeg.input(file) for file in temp_files]
            ffmpeg.concat(*input_files, v=0, a=1).output(
                filename, loglevel="error"
            ).run(overwrite_output=True)

            for item, segment_length in zip(items_to_process, segment_lengths):
                text = str(item.get("text", ""))

                if isinstance(text, str):
                    self.item_data.append((segment_length * 1e9, text))

            self.backend.cleanup()
            sys.stdout.write("\n")

            num_zeros = len(str(len(self.temp_files)))
            title = chapter.get("title", "Chapter")
            chapter_title = f"{c + 1:0{num_zeros}} - {title}"
            filename_out = os.path.join(temp_dir, f"tts_part_{c}.{temp_format}")

            self.temp_files.append((chapter_title, filename_out))
            logger.info(f"Temp file added: {filename_out}")

            segment_length = self._get_nanoseconds_for_file(filename)
            end_time = cumulative_time + segment_length
            self.chapter_times.append((cumulative_time, end_time))
            cumulative_time = end_time

    def _split_sentences_by_speed(
        self, sentences: List[str]
    ) -> Tuple[Dict[int, Dict[str, Any]], bool]:
        synthesize_splitted = False
        sentence_data: Dict[int, Dict[str, Any]] = {}

        for i, sentence in enumerate(sentences):
            letter_count = len(sentence)
            # speed_slider = self.voices[voice_id].get("speed_slider", 1.0)
            speed_slider = 1.0
            speed_slider_max = speed_slider

            if letter_count > 0 and letter_count < 100:
                speed_slider = 0.3 + (speed_slider - 0.3) * (letter_count / 100)
                speed_slider = min(speed_slider_max, speed_slider)
                speed_slider = max(0.5, speed_slider)

                if speed_slider < 1.0:
                    synthesize_splitted = True

            sentence_data[i] = {
                "sentence": sentence,
                "speed_slider": speed_slider,
            }

        return sentence_data, synthesize_splitted

    def concatenate_bytes(self, byte_obj1: bytes, byte_obj2: bytes) -> bytes:
        concatenated_bytes = byte_obj1 + byte_obj2
        return concatenated_bytes

    def pad_length(self, numpy_wav: np.ndarray, duration: float) -> np.ndarray:
        """
        Pad a numpy array of audio samples with zeros to achieve a desired duration.

        :param numpy_wav: A 1D numpy array of audio samples.
        :type numpy_wav: np.ndarray

        :param duration: The desired duration of the audio in seconds.
        :type duration: float

        :return: A 1D numpy array of padded audio samples with the desired duration.
        :rtype: np.ndarray
        """
        sample_rate = self.sample_rate
        current_duration = len(numpy_wav) / sample_rate
        if current_duration < duration:
            padding_duration = duration - current_duration
            padding_samples = int(padding_duration * sample_rate)
            numpy_wav = np.pad(numpy_wav, (0, padding_samples), "constant")
        return numpy_wav

    def _get_nanoseconds_for_file(self, filename: str) -> int:
        """
        Get the duration of an audio file in nanoseconds.

        :param filename: The file name (including path) of the audio file to get the duration of.
        :type filename: str

        :return: The duration of the audio file in nanoseconds.
        :rtype: int
        """
        result = ffmpeg.probe(filename, cmd="ffprobe", show_entries="format=duration")
        return int(float(result["format"]["duration"]) * self.NANOSECONDS_IN_ONE_SECOND)

    def process_item(
        self, item: Dict[str, Any], mapped_speaker_id: Dict[str, Any]
    ) -> np.ndarray:
        numpy_wav = np.array([0], dtype=np.float32)

        if item.get("text", "").strip():
            model = ""

            if isinstance(self.backend, TTSBackendF5):
                frames = self.backend.synthesize(item["text"], mapped_speaker_id)

                numpy_wav = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                numpy_wav /= np.iinfo(np.int16).max

                del frames

        numpy_wav = self.pad_length(numpy_wav, item.get("min_length", 0) / 1000)

        return numpy_wav

    def process_items(self, items: List[TextItem]) -> Tuple[List[str], List[float]]:
        temp_files = []
        segment_lengths = []

        if isinstance(self.backend, TTSBackendF5):
            self.current_item_count = len(items)
            numpy_segments = self.backend.synthesize_batch(items)

            for i, numpy_segment in enumerate(numpy_segments):
                min_length = items[i].get("min_length", 0)

                if isinstance(min_length, int):
                    numpy_segment = self.pad_length(numpy_segment, min_length / 1000)

                temp_file_path = f"{self.temp_dir}/{i}.wav"
                scipy.io.wavfile.write(temp_file_path, self.sample_rate, numpy_segment)
                temp_files.append(temp_file_path)

                segment_length = len(numpy_segment) / self.sample_rate
                segment_lengths.append(segment_length)

        return temp_files, segment_lengths

    def synthesize_project(
        self,
        json_path: str,
        title: str = "",
        temp_dir_prefix: Optional[str] = "",
        max_pause_duration: int = 1500,
        subtitles: bool = False,
    ) -> None:

        logger.info(f'Loading project from "{json_path}"')

        project = self.load_json(json_path)

        logger.info("Preparing TTS")

        chapters = self.get_chapters(project)
        self.replace: Dict[str, str] = {}
        source_dir = Path(__file__).resolve().parent
        lang = "en"

        for file_path in [
            os.path.join("data", "replace.json"),
            os.path.join("data", f"replace_{lang}.json"),
        ]:

            with open(
                os.path.join(source_dir, file_path), "r", encoding="utf-8"
            ) as file:
                data = file.read()
                self.replace.update(json.loads(data))

        tts_preprocessor = TTS_Preprocessor()

        for chapter in chapters:
            chapter["items"] = tts_preprocessor.optimize(
                chapter.get("items", []), max_pause_duration=max_pause_duration
            )
            chapter["items"] = tts_preprocessor.preprocess(
                chapter.get("items", []), self.replace
            )

        if temp_dir_prefix:
            if not os.path.exists(temp_dir_prefix):
                os.makedirs(temp_dir_prefix)
        else:
            temp_dir_prefix = None

        logger.info(f"Synthesizing project \"{project['title']}\"")

        with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as temp_dir:
            try:
                self.synthesize_chapters(chapters, temp_dir)
            except Exception as e:
                logger.error(f"Error synthesizing project: {e}")
                return
            else:
                ffmpeg_processor = FFmpegProcessor(
                    self.temp_files,
                    self.chapter_times,
                    self.item_data,
                    self.project_path,
                    self.output_format,
                )
                ffmpeg_processor.process_ffmpeg(project, title, temp_dir, subtitles)

        logger.success("Project synthesis complete")


def new_item(
    text: str,
    min_length: float = 0.0,
    speaker_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "text": text,
        "min_length": min_length,
        "speaker_id": speaker_id,
    }


def new_pause_item(duration: float) -> Dict[str, Any]:
    return {
        "min_length": duration,
    }


def save_tts_project_to_json(tts_project: TTS_Project, output_filename: str) -> None:
    # Get path from filename
    output_path = os.path.dirname(output_filename)

    # Create directory if needed
    os.makedirs(output_path, exist_ok=True)

    with open(output_filename, "w") as file:
        json.dump(tts_project_to_json(tts_project, output_path), file, indent=4)


def tts_project_to_json(
    tts_project: TTS_Project,
    output_path: str,
    backend_voices: Dict[str, Any] = {},
) -> Dict[str, Any]:
    # Save image
    image_path = None
    if tts_project.image_bytes:
        image_path = os.path.join(output_path, "cover.jpg")
        image_bytes = base64.b64decode(tts_project.image_bytes)

        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)

    chapters_dict: List[Dict[str, Any]] = []

    for chapter in tts_project.tts_chapters:
        items_dict: List[Dict[str, Any]] = []

        for item in chapter.tts_items:
            item_dict: Dict[str, Any] = {}
            if item.text:
                item_dict = new_item(
                    text=item.text,
                    min_length=item.length,
                    speaker_id=str(item.speaker_idx),
                )
            elif item.length:
                item_dict = new_pause_item(item.length)

            items_dict.append(item_dict)

        chapters_dict.append({"title": chapter.title, "items": items_dict})

    post_date = tts_project.date

    if post_date is None:
        post_date = date.today()

    project = {
        "title": tts_project.title,
        "subtitle": tts_project.subtitle,
        "author": tts_project.author,
        "date": post_date.isoformat(),
        "chapters": chapters_dict,
        "backend": {},
    }

    if image_path:
        project["cover_image"] = image_path

    project["backend"] = backend_voices

    return project
