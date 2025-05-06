import asyncio
import base64
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import ffmpeg  # type: ignore
import numpy as np
import scipy  # type: ignore
from loguru import logger

from tts_arranger.functions import load_default_config
from tts_arranger.items.tts_chapter import TTS_Chapter
from tts_arranger.items.tts_element import TTS_Element
from tts_arranger.items.tts_item import TTS_Item
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.tts_backend import TTSBackend
from tts_arranger.tts_preprocessor import TTS_Preprocessor  # type: ignore

from .ffmpeg_processor import FFmpegProcessor
from .items.tts_project import TTS_Project  # type: ignore

TextItem = Dict[str, str | float]


class TTS_Processor:
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
        self.chapter_times: List[Tuple[int, int]] = []
        self.item_data: List[Tuple[int, str]] = []
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

        if speaker_id_mapping and speaker_id_mapping != {}:
            self.backend_config["speaker_id_mapping"] = speaker_id_mapping

        self.sample_rate = self.backend_config.get("sample_rate", 24000)

        self.current_item_count = 0
        self.current_chapter_count = 0
        self.current_chapter_idx = 0

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

    def prepare_text_items(self, items: List[TTS_Item]) -> List[TextItem]:
        text_items: List[TextItem] = []

        for item in items:
            for element in item.elements:
                text_item: Dict[str, str | float] = {}
                if element.text:
                    text_item["text"] = element.text
                if element.min_length:
                    text_item["min_length"] = element.min_length
                if element.speaker_id:
                    text_item["speaker_id"] = element.speaker_id

                text_items.append(text_item)

        return text_items

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?]) +|\n", text.strip())

        merged_sentences = []

        i = 0
        while i < len(sentences):
            # If the sentence only contains a single uppercase letter and a dot, merge it with the previous and next sentence
            if re.match(r"^[A-Z]\.$", sentences[i].strip()):
                if i > 0 and i < len(sentences) - 1:
                    if not merged_sentences:
                        merged_sentences.append(sentences[i - 1])
                    merged_sentences[-1] = (
                        f"{merged_sentences[-1]} {sentences[i]} {sentences[i+1]}"
                    )
                    i += 1  # Skip the next sentence as it has been merged
            else:
                merged_sentences.append(sentences[i])
            i += 1

        return merged_sentences

    def batch_process_temp_files(
        self,
        temp_files: List[str],
        temp_dir: str,
        temp_format: str,
        filename: str,
        items_to_process: List[TextItem],
        segment_lengths: List[float],
    ) -> None:
        # Batch process the temp files to avoid ffmpeg concat issues with large number of files

        batch_size = 500
        batched_temp_files = [
            temp_files[i : i + batch_size]
            for i in range(0, len(temp_files), batch_size)
        ]
        intermediate_files: List[str] = []

        for batch_idx, batch in enumerate(batched_temp_files):
            batch_filename = os.path.join(temp_dir, f"batch_{batch_idx}.{temp_format}")
            input_files = [ffmpeg.input(file) for file in batch]
            ffmpeg.concat(*input_files, v=0, a=1).output(
                batch_filename, loglevel="error"
            ).run(overwrite_output=True)
            intermediate_files.append(batch_filename)

        final_input_files = [ffmpeg.input(file) for file in intermediate_files]
        ffmpeg.concat(*final_input_files, v=0, a=1).output(
            filename, loglevel="error"
        ).run(overwrite_output=True)

    async def synthesize_chapters(
        self,
        chapters: List[TTS_Chapter],
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

            logger.info(f"Processing chapter {c+1} of {len(chapters)}: {chapter.title}")
            filename = os.path.join(temp_dir, f"tts_part_{c}.{temp_format}")
            items: List[TextItem] = self.prepare_text_items(chapter.items)

            match self.backend_config["backend_id"]:
                case "edge-tts":
                    from .tts_backend_edge_tts import TTSBackendEdge

                    self.backend = TTSBackendEdge(
                        "edge-tts", self.temp_dir, self.backend_config, self.on_progress
                    )
                case "kokoro-tts":
                    from .tts_backend_kokoro import TTSBackendKokoro

                    self.backend = TTSBackendKokoro(
                        "kokoro", self.temp_dir, self.backend_config, self.on_progress
                    )
                case "kokoro-tts-gradio":
                    from .tts_backend_kokoro_gradio import TTSBackendKokoroGradio

                    self.backend = TTSBackendKokoroGradio(
                        "kokoro", self.temp_dir, self.backend_config, self.on_progress
                    )
                case _:
                    from .tts_backend_f5 import TTSBackendF5

                    self.backend = TTSBackendF5(
                        "f5-tts", self.temp_dir, self.backend_config, self.on_progress
                    )

            items_to_process: List[TextItem] = []

            if len(items) == 0:
                logger.warning("No items to process, skipping chapter")
                continue

            for i, item in enumerate(items):
                # text = ""

                # if "text" in item:
                #     text = str(item.get("text", ""))

                #     if not isinstance(text, str):
                #         continue
                # else:
                #     if "min_length" in item:
                #         items_to_process.append(item)
                #     else:
                #         continue

                # if not text.strip():
                #     continue

                # # sentences = re.split(r"(?<=[.!?]) +|\n", text.strip())
                # sentences = self.split_sentences(text)
                # # speaker_id_mapping = deepcopy(self.backend_data["speaker_id_mapping"])
                # # speaker_id = item.get("speaker_id", None)

                # # if speaker_id in speaker_id_mapping:
                # #     voice_id = speaker_id_mapping[speaker_id]
                # # else:
                # #     voice_id = list(speaker_id_mapping.values())[0]

                # sentence_data, synthesize_splitted = self._split_sentences_by_speed(
                #     sentences
                # )

                # if synthesize_splitted:
                #     for i, sentence in sentence_data.items():
                #         item = {
                #             "text": sentence["sentence"],
                #             "min_length": 0,
                #             "speaker_id": item["speaker_id"],
                #             "speed_slider": sentence["speed_slider"],
                #         }
                #         # speaker_id_mapping_copy = deepcopy(speaker_id_mapping)
                #         # voice_id = speaker_id_mapping_copy.get(speaker_id, None)

                #         items_to_process.append(item)
                # else:
                #     item = {
                #         "text": text,
                #         "min_length": item.get("min_length", 0),
                #         "speaker_id": item["speaker_id"],
                #     }

                items_to_process.append(item)

            temp_files, segment_lengths = await self.process_items(items_to_process)

            self.batch_process_temp_files(
                temp_files,
                temp_dir,
                temp_format,
                filename,
                items_to_process,
                segment_lengths,
            )

            for item, segment_length in zip(items_to_process, segment_lengths):
                text = str(item.get("text", ""))

                if isinstance(text, str):
                    self.item_data.append((int(segment_length * 1e9), text))

            self.backend.cleanup()
            sys.stdout.write("\n")

            num_zeros = len(str(len(self.temp_files)))
            title = chapter.title
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

            if isinstance(self.backend, TTSBackend):
                frames = self.backend.synthesize(item["text"], mapped_speaker_id)

                numpy_wav = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                numpy_wav /= np.iinfo(np.int16).max

                del frames

        numpy_wav = self.pad_length(numpy_wav, item.get("min_length", 0) / 1000)

        return numpy_wav

    async def process_items(
        self, items: List[TextItem]
    ) -> Tuple[List[str], List[float]]:
        temp_files = []
        segment_lengths = []

        if isinstance(self.backend, TTSBackend):
            self.current_item_count = len(items)
            await self.backend.synthesize_batch(items)
            numpy_segments = self.backend.results

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

    async def _synthesize_project(
        self,
        project: TTS_Project,
        title: str = "",
        temp_dir_prefix: Optional[str] = "",
        subtitles: bool = False,
    ) -> None:
        logger.info("Preparing TTS")

        chapters = project.chapters
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
            chapter.items = tts_preprocessor.preprocess(chapter.items, self.replace)

        if temp_dir_prefix:
            if not os.path.exists(temp_dir_prefix):
                os.makedirs(temp_dir_prefix)
        else:
            temp_dir_prefix = None

        logger.info(f'Synthesizing project "{project.title}"')

        with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as temp_dir:
            try:
                await self.synthesize_chapters(chapters, temp_dir)
            except Exception as e:
                logger.error(f"Error synthesizing project: {e}")
                raise
            else:
                if self.temp_files:
                    ffmpeg_processor = FFmpegProcessor(
                        self.temp_files,
                        self.chapter_times,
                        self.item_data,
                        self.project_path,
                        self.output_format,
                    )
                    ffmpeg_processor.process_ffmpeg(project, title, temp_dir, subtitles)
                    logger.success("Project synthesis complete")
                else:
                    logger.warning("No synthesized files found, skipping project")

    def synthesize_project(
        self,
        project: TTS_Project,
        title: str = "",
        temp_dir_prefix: Optional[str] = "",
        subtitles: bool = False,
    ) -> None:
        asyncio.run(
            self._synthesize_project(
                project,
                title=title,
                temp_dir_prefix=temp_dir_prefix,
                subtitles=subtitles,
            )
        )
