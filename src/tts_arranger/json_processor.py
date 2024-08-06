import base64
from cmath import sqrt
import io
import json
import math
import os
import subprocess
import tempfile
import wave
import srt
from pathlib import Path
from typing import Optional

import ffmpeg  # type: ignore
import numpy as np
import scipy  # type: ignore
from pathvalidate import sanitize_filename
from PIL import Image
from piper import PiperVoice  # type: ignore
from piper.download import find_voice, get_voices  # type: ignore

from .items.tts_project import TTS_Project  # type: ignore
from .utils.log import LOG_TYPE, bcolors, log  # type: ignore


class JSON_Processor:
    def __init__(self, base_path: str, output_format="m4b"):
        self.NANOSECONDS_IN_ONE_SECOND = 1e9

        self.download_dir = "/usr/share/piper-voices/"
        self.sample_rate = 22050
        self.temp_files: list[tuple[str, str]] = []
        self.chapter_times: list[tuple[float, float]] = []
        self.item_data: list[tuple[float, str]] = []
        self.project_path = base_path
        self.output_format = output_format
        self.backend_properties: dict = {}

    def load_json(self, json_path: str) -> dict:
        with open(json_path, "r") as file:
            json_data = json.load(file)
        return json_data

    def get_chapters(self, json_data) -> list[dict]:
        return json_data.get("chapters", [])

    def get_model_info(self, json_data) -> dict:
        model_ids: dict = {}
        self.backend_properties = json_data.get("backend", {})
        backend_id: str = self.backend_properties.get("backend_id", "")
        speaker_id_mapping: dict = self.backend_properties.get("speaker_id_mapping", {})

        for _, model in speaker_id_mapping.items():
            if backend_id not in model_ids:
                model_ids[backend_id] = []
            if model not in model_ids[backend_id]:
                model_ids[backend_id].append(model)
        return model_ids

    def load_models(self, model_ids) -> dict:
        voices = {}
        for backend in model_ids:
            if backend == "piper":
                for model_id in model_ids[backend]:
                    model_id_value = model_id["model_id"]
                    voices[model_id_value] = self.load_model(backend, model_id_value)
        return voices

    def load_model(self, backend, model_id) -> PiperVoice:
        voices_info = get_voices(self.download_dir, update_voices=False)
        file = self.download_dir + list(voices_info[model_id]["files"].keys())[0]
        dir = Path(str(file)).parent
        model_id_path, config = find_voice(model_id, [dir])
        voice = PiperVoice.load(model_id_path, config_path=config, use_cuda=False)
        log(LOG_TYPE.INFO, f"Loaded voice {model_id} from {config}")
        with open(config, "r", encoding="utf-8") as config_file:
            config_dict = json.load(config_file)
            sample_rate = config_dict["audio"]["sample_rate"]
            if sample_rate > self.sample_rate:
                self.sample_rate = sample_rate
        return voice

    def synthesize_chapters(self, chapters: list[dict], voices, temp_dir="/tmp"):
        # total_items = sum(len(chapter.get("items", [])) for chapter in chapters)

        temp_format = "wav"

        cumulative_time: float = 0

        # Preset the first segment data
        self.item_data.append((0, ""))

        for c, chapter in enumerate(chapters):
            log(
                LOG_TYPE.INFO,
                f"Processing chapter {c+1} of {len(chapters)}: {chapter.get('title', 'Chapter')}",
            )
            numpy_segments = np.array([0], dtype=np.float32)
            filename = os.path.join(temp_dir, f"tts_part_{c}.{temp_format}")
            items = chapter.get("items", [])
            for i, item in enumerate(items):
                log(
                    LOG_TYPE.INFO,
                    f"Processing item {i+1} of {len(items)} [Speaker: {item.get('speaker_id', '(Pause)')}]",
                )

                numpy_segment = self.process_item(item, voices)
                numpy_segments = np.concatenate((numpy_segments, numpy_segment))

                # Get length of numpy segment in nanoseconds
                segment_length = len(numpy_segment) / self.sample_rate * 1e9

                self.item_data.append((segment_length, item.get("text", "")))

            scipy.io.wavfile.write(filename, self.sample_rate, numpy_segments)

            num_zeros = len(str(len(self.temp_files)))
            title = chapter.get("title", "Chapter")
            chapter_title = f"{c + 1:0{num_zeros}} - {title}"
            filename_out = os.path.join(temp_dir, f"tts_part_{c}.{temp_format}")

            # Add temp file for concatenating later
            self.temp_files.append((chapter_title, filename_out))
            log(LOG_TYPE.INFO, f"Temp file added: {filename_out}{bcolors.ENDC}")

            segment_length = self._get_nanoseconds_for_file(filename)

            end_time = cumulative_time + segment_length
            self.chapter_times.append((cumulative_time, end_time))
            cumulative_time = end_time

    def _merge_items(self, tts_items: list[dict]) -> list[dict]:
        final_items: list[dict] = []
        merged_item: Optional[dict] = None

        for tts_item in tts_items:
            if not merged_item:
                # Scanning not started
                merged_item = tts_item
            elif merged_item.get("speaker_id", "") == tts_item.get("speaker_id", ""):
                # Starting item and current are similar, add to merge item text and length
                merged_item = {
                    "text": f'{merged_item.get("text", "")} {tts_item.get("text", "")}',
                    "speaker_id": merged_item.get("speaker_id", ""),
                    "min_length": merged_item.get("min_length", 0)
                    + tts_item.get("min_length", 0),
                }
            else:
                # Starting item and current are not similar, add last and current item, set this item as new starting item
                final_items.append(merged_item)
                merged_item = tts_item

        if merged_item is not None:
            final_items.append(merged_item)

        return final_items

    def preprocess(self, tts_items: list[dict]) -> list[dict]:
        # final_items: list[dict] = []
        for item in tts_items:
            if item.get("text"):
                # Replace hyphen variants with standard hyphen
                item["text"] = item["text"].replace(" – ", " - ")
                item["text"] = item["text"].replace("—", " - ")

                # Replace standard hyphen with two line breaks
                item["text"] = item["text"].replace(" - ", "\n\n")

                # Same with brackets
                item["text"] = item["text"].replace("(", "\n\n")
                item["text"] = item["text"].replace(")", "\n\n")

                # Miscellanous replacements
                item["text"] = item["text"].replace("…", "\n\n")

                # Make sure each item ends with space
                item["text"] = item["text"].strip() + " "

        return tts_items

    def optimize(self, tts_items: list[dict], max_pause_duration=0) -> list[dict]:
        """
        Merge similar items for smoother synthesizing and avoiding unwanted pauses

        :param max_pause_duration: Maximum duration auf merged pauses
        :type max_pause_duration: int

        :return: None
        """

        final_items: list[dict] = self._merge_items(tts_items)

        non_empty_items: list[dict] = []

        # Remove remaining empty items
        for final_item in final_items:
            stripped_text = final_item.get("text", "").strip()
            if stripped_text or final_item.get("min_length", 0) > 0:
                # if stripped_text:
                #     final_item["text"] = stripped_text
                non_empty_items.append(final_item)

        # Merge one final time for remaining pauses
        non_empty_items = self._merge_items(non_empty_items)

        # Limit pause duration for pause items, ignore if max_pause_duration == 0
        for non_empty_item in non_empty_items:
            if non_empty_item.get("speaker_id") == -1 and max_pause_duration > 0:
                if non_empty_item.get("min_length", 0) > max_pause_duration:
                    non_empty_item["min_length"] = max_pause_duration

        return non_empty_items

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

    def _get_nanoseconds_for_file(self, filename: str):
        """
        Get the duration of an audio file in nanoseconds.

        :param filename: The file name (including path) of the audio file to get the duration of.
        :type filename: str

        :return: The duration of the audio file in nanoseconds.
        :rtype: int
        """
        result = ffmpeg.probe(filename, cmd="ffprobe", show_entries="format=duration")
        return int(float(result["format"]["duration"]) * self.NANOSECONDS_IN_ONE_SECOND)

    def process_item(self, item, voices):
        numpy_wav = np.array([0], dtype=np.float32)

        if item.get("text", "").strip():
            synthesize_args = {
                "speaker_id": None,
                "length_scale": None,
                "noise_scale": None,
                "noise_w": None,
                "sentence_silence": 0.5,
            }

            mapped_speaker_id = self.backend_properties["speaker_id_mapping"].get(
                item["speaker_id"]
            )

            model = ""
            volume_factor = 1.0

            if mapped_speaker_id:
                synthesize_args["speaker_id"] = mapped_speaker_id.get(
                    "speaker_id", None
                )
                model = mapped_speaker_id.get("model_id", "")
                volume_factor = mapped_speaker_id.get("volume_factor", 1.0)
            else:
                # Speaker ID not mapped, fall back to first model
                model = list(voices.keys())[0]
                log(
                    LOG_TYPE.WARNING,
                    f"Speaker ID {item['speaker_id']} not found, falling back to model {model}",
                )

            # TODO: Find a better way to handle this
            wave_io = io.BytesIO()
            with wave.open(wave_io, "wb") as wav_file:
                voices[model].synthesize(item["text"], wav_file, **synthesize_args)
            wave_io.seek(0)
            with wave.open(wave_io, "rb") as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
            numpy_wav = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            numpy_wav /= np.iinfo(np.int16).max

            volume_factor_log = pow(
                2, (sqrt(sqrt(sqrt(volume_factor))) * 192 - 192) / 6
            )

            np.multiply(numpy_wav, volume_factor_log, out=numpy_wav, casting="unsafe")

        # Pad with zeros to reach the desired length
        numpy_wav = self.pad_length(numpy_wav, item.get("min_length", 0) / 1000)

        return numpy_wav

    def synthesize_project(
        self,
        json_path: str,
        title: str = "",
        temp_dir_prefix: str | None = "",
        max_pause_duration=1500,
        subtitles: bool = False,
    ):
        log(LOG_TYPE.INFO, f'Loading project from "{json_path}"')
        project = self.load_json(json_path)

        log(LOG_TYPE.INFO, "Preparing TTS")
        chapters = self.get_chapters(project)

        for chapter in chapters:
            chapter["items"] = self.optimize(
                chapter.get("items", []), max_pause_duration=max_pause_duration
            )
            chapter["items"] = self.preprocess(chapter.get("items", []))

        model_ids = self.get_model_info(project)
        voices = self.load_models(model_ids)

        # Make sure temp prefix exists
        if temp_dir_prefix:
            if not os.path.exists(temp_dir_prefix):
                os.makedirs(temp_dir_prefix)
        else:
            # tempfile.TemporaryDirectory needs None, otherwise this will be set to the current working directory
            temp_dir_prefix = None

        log(LOG_TYPE.INFO, f"Synthesizing project \"{project['title']}\"")
        with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as temp_dir:
            try:
                self.synthesize_chapters(chapters, voices, temp_dir)
            except Exception as e:
                log(LOG_TYPE.ERROR, f"Error synthesizing project: {e}")
                return
            else:
                if len(self.temp_files) > 0:
                    log(LOG_TYPE.INFO, "Preparing metadata")
                    metadata_lines = [";FFMETADATA1\n"]

                    for c, chapter in enumerate(chapters):
                        chapter_times = self.chapter_times[c]
                        chapter_title = chapter.get("title", f"Chapter {c + 1}")
                        metadata_lines.append(
                            f"[CHAPTER]\nSTART={chapter_times[0]}\nEND={chapter_times[1]}\ntitle={chapter_title}\n"
                        )

                    metadata = "".join(metadata_lines)
                    metadata_filename = os.path.join(temp_dir, "metadata")

                    # Write all custom metadata to the new metadata file
                    with open(
                        metadata_filename, "w", encoding="utf-8"
                    ) as metadata_file:
                        metadata_file.write(metadata)

                    # Get project title
                    if title == "":
                        title = project.get("title", "Untitled Project")

                    output_filename = os.path.join(
                        self.project_path, sanitize_filename(title)
                    )
                    output_extension = f".{self.output_format}"

                    # Shorten path if needed
                    output_filename = output_filename[: 255 - len(output_extension)]
                    output_path = output_filename + output_extension

                    output_files: list[str] = []

                    # Create directory if needed
                    os.makedirs(self.project_path, exist_ok=True)

                    infiles = [ffmpeg.input(file) for _, file in self.temp_files]

                    metadata_input = ffmpeg.input(metadata_filename)

                    if self.output_format not in ["m4b", "m4a"]:
                        log(
                            LOG_TYPE.WARNING,
                            f"Chapters are only possible for m4b/m4a at the moment.",
                        )

                    project_title = project.get("title", "TTS Project")
                    project_subtitle = project.get("subtitle", "")
                    project_author = project.get("author", "")

                    log(LOG_TYPE.INFO, "Converting to final output")

                    cmd = (
                        ffmpeg.concat(*infiles, v=0, a=1)
                        # .filter('speechnorm', e=f'{comp_expansion}', r=f'{comp_raise}', l=1)
                        .output(
                            metadata_input,
                            output_path,
                            map_metadata=1,
                            **{
                                "metadata": f"title={project_title}",
                                "metadata:": f"album={project_subtitle}",
                                "metadata:g": f"artist={project_author}",
                            },
                            loglevel="error",
                        ).compile(overwrite_output=True)
                    )

                    # Remove last map parameter (workaround for ffmpeg-python bug)
                    cmd = self._remove_last_arg(cmd, "-map")

                    subprocess.call(cmd)

                    output_files.append(output_path)
                    log(
                        LOG_TYPE.SUCCESS,
                        f'Synthesizing project "{project_title}" finished, file saved as "{output_path}".',
                    )

                    if "cover_image" in project:
                        # Load image from path

                        try:
                            with Image.open(project["cover_image"]) as image:
                                if image.format:
                                    image_added = False
                                    for output_file in output_files:
                                        # Add image
                                        output_path_with_image = (
                                            output_file + "_tmp" + output_extension
                                        )

                                        self._add_image(
                                            image, output_file, output_path_with_image
                                        )
                                        os.remove(output_file)
                                        os.rename(output_path_with_image, output_file)
                                        image_added = True

                                    if image_added:
                                        log(
                                            LOG_TYPE.SUCCESS,
                                            "Project image added to final output for all files.",
                                        )
                        except Image.UnidentifiedImageError:
                            log(
                                LOG_TYPE.ERROR,
                                f"Could not add image to final output, image file is not a valid image file.",
                            )

                    if subtitles:
                        # Write SRT from segments data
                        srt_output_file = os.path.splitext(output_path)[0] + ".srt"

                        srt_data = []
                        start_time: float = 0

                        for i, segment_data in enumerate(self.item_data):
                            # Get segment length in microseconds (from nanoseconds)
                            segment_length = segment_data[0] / 1000
                            segment_data_str = segment_data[1].strip()

                            if segment_data_str != "":
                                subtile_data = srt.Subtitle(
                                        index=i + 1,
                                        start=srt.timedelta(microseconds=start_time),
                                        end=srt.timedelta(microseconds=start_time + segment_length),
                                        content=segment_data_str,
                                    )
                            
                                srt_data.append(subtile_data)
                            start_time += segment_length

                        log(LOG_TYPE.INFO, f"Writing SRT to {srt_output_file}")

                        with open(srt_output_file, "w", encoding="utf-8") as srt_file:
                            srt_file.write(srt.compose(srt_data))
                # if numpy_segments.size > 1:
                #     log(LOG_TYPE.INFO, "Writing output to /tmp/output")
                #     self._write(numpy_segments, "/tmp/output")
        log(LOG_TYPE.SUCCESS, "Project synthesis complete")

    def _remove_last_arg(self, cmd: list[str], arg: str) -> list[str]:
        """
        Remove the last occurrence of the given argument from the provided list.

        :param cmd: A list of strings to be searched and modified.
        :type cmd: list of str

        :param arg: A string representing the argument to be removed from `cmd`.
        :type arg: str

        :return: A modified version of the original list `cmd` with the last occurrence of `arg` removed.
        :rtype: list of str

        :raises ValueError: If `cmd` is empty or `arg` is not found in `cmd`.
        """

        if cmd:
            cmd.reverse()

            index = cmd.index(arg)

            if index:
                cmd.pop(index - 1)
                cmd.pop(index - 1)

            cmd.reverse()
        return cmd

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

    def _add_image(self, image: Image.Image, input_file: str, output_file: str) -> None:
        """
        Add an image to the final audio file and save the result to a new file.

        :param image: The image to add to the audio file.
        :type image: PIL.Image.Image

        :param input_file: The path to the input audio file.
        :type input_file: str

        :param output_file: The path to save the resulting audio file.
        :type output_file: str
        :return: None

        :raises: ValueError if the provided `image` is not a PIL Image instance, or if either `input_file` or `output_file` are not valid file paths.
        """

        image_width, image_height = image.size

        with tempfile.TemporaryDirectory() as temp_dir:
            audio = ffmpeg.input(input_file)["a"]

            # Save the project as a temporary image
            image_format = "jpeg"

            image_path = os.path.join(temp_dir, f"tts_image.{image_format}")

            if image.format == "PNG" and image.mode != "RGBA":
                image = image.convert("RGBA")
                background = Image.new("RGBA", image.size, (255, 255, 255))
                image = Image.alpha_composite(background, image)

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Fix for ffmpeg problem when image size is not divisible by 2
            image.crop(
                (0, 0, math.ceil(image_width / 2) * 2, math.ceil(image_height / 2) * 2)
            ).save(image_path, format=image_format, quality=90)

            cover = ffmpeg.input(image_path)["v"]

            (
                ffmpeg.output(
                    audio,
                    cover,
                    output_file,
                    vcodec="copy",
                    acodec="copy",
                    map_metadata=0,
                    **{"disposition:v:0": "attached_pic"},
                    loglevel="error",
                ).run(overwrite_output=True)
            )


def new_item(
    text: str,
    min_length: float = 0.0,
    speaker_id=None,
):
    return {
        "text": text,
        "min_length": min_length,
        "speaker_id": speaker_id,
    }


def new_pause_item(duration: float):
    return {
        "min_length": duration,
    }


def save_tts_project_to_json(tts_project: TTS_Project, output_filename: str):
    # Get path from filename
    output_path = os.path.dirname(output_filename)

    # Create directory if needed
    os.makedirs(output_path, exist_ok=True)

    with open(output_filename, "w") as file:
        json.dump(tts_project_to_json(tts_project, output_path), file, indent=4)


def tts_project_to_json(
    tts_project: TTS_Project,
    output_path: str,
    backend: str = "piper",
    model_id: str = "",
    speaker_id_mapping: dict = {},
) -> dict:
    # Save image
    image_path = None
    if tts_project.image_bytes:
        image_path = os.path.join(output_path, "cover.jpg")
        image_bytes = base64.b64decode(tts_project.image_bytes)

        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)

    chapters_dict = []

    for chapter in tts_project.tts_chapters:
        items_dict = []

        for item in chapter.tts_items:
            item_dict: dict = {}
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

    project = {
        "title": tts_project.title,
        "subtitle": tts_project.subtitle,
        "author": tts_project.author,
        "date": tts_project.date.isoformat(),
        "chapters": chapters_dict,
        "backend": {},
    }

    if image_path:
        project["cover_image"] = image_path

    if backend == "piper":
        backend_dict: dict = {
            "backend_id": backend,
            "speaker_id_mapping": speaker_id_mapping,
        }

        project["backend"] = backend_dict

    return project
