import base64
import io
import math
import os
import subprocess
import sys
import tempfile
from typing import Callable, Optional

import ffmpeg  # type: ignore
from pathvalidate._filename import sanitize_filename
from PIL import Image
from pydub import AudioSegment  # type: ignore

from .items.tts_chapter import TTS_Chapter  # type: ignore
from .items.tts_item import TTS_Item  # type: ignore
from .items.tts_project import TTS_Project  # type: ignore
from .tts_processor import TTS_Processor
from .utils.log import LOG_TYPE, bcolors, log  # type: ignore


class TTS_Writer():
    """
    Class to process TTS projects (containing of chapters each containing a number of items) and to finally write an audio file including chapter metadata and chapter info
    """

    def __init__(self, project: TTS_Project = TTS_Project(),  base_path: str = '', output_format='m4b', model: str = '', vocoder: str = '', preferred_speakers: Optional[list[str]] = None) -> None:
        """
        Constructor for the TTS_Writer class.

        :param project: An instance of the TTS_Project class containing the project information.
        :type project: TTS_Project

        :param base_path: The path to the project directory.
        :type base_path: str

        :param output_format: The desired output format of the final audio file. Default is 'm4b'.
        :type output_format: str

        :param model: The name of the model to be used. Default is an empty string.
        :type model: str

        :param vocoder: The name of the vocoder to be used. Default is an empty string.
        :type vocoder: str
        :return: None
        """
        self.NANOSECONDS_IN_ONE_SECOND = 1e9

        self.project = project
        self.project_path = base_path
        self.output_format = output_format
        self.model = model
        self.vocoder = vocoder

        self.temp_files: list[tuple[str, str]] = []
        self.preferred_speakers = preferred_speakers or []

    def _get_nanoseconds_for_file(self, file_name):
        """
        Get the duration of an audio file in nanoseconds.

        :param file_name: The file name (including the path) of the audio file to get the duration of.
        :type file_name: str

        :return: The duration of the audio file in nanoseconds.
        :rtype: int
        """
        result = ffmpeg.probe(file_name, cmd='ffprobe', show_entries='format=duration')
        return int(float(result['format']['duration']) * self.NANOSECONDS_IN_ONE_SECOND)

    def _synthesize_chapters(self, chapters: list[TTS_Chapter], temp_dir: str, tts_processor: TTS_Processor, callback: Callable[[float, TTS_Item], None] | None = None) -> None:
        """
        Private method for synthesizing chapters into audio.

        :param chapters: A list of TTS chapters containing text to be synthesized into audio.
        :type chapters: list[TTS_Chapter]

        :param temp_dir: Path to the temporary directory.
        :type temp_dir: str

        :param tts_arranger: ATTS_Arranger object to be used for synthesizing.
        :type tts_arranger: TTS_Arranger

        :param callback: An optional function that can be used to monitor the progress of the synthesis process.
        :type callback: Callable[[float, TTS_Item], None] | None

        :return: None
        :rtype: None
        """

        log(LOG_TYPE.INFO, f'Preprocessing items')

        for chapter in chapters:
            chapter.tts_items = tts_processor.preprocess_items(chapter.tts_items)

        tts_processor.initialize()

        total_items = 0

        for chapter in chapters:
            total_items += len(chapter.tts_items)

        current_total_items = 0

        cumulative_time = 0

        for i, chapter in enumerate(chapters):
            audio = AudioSegment.empty()

            temp_format = 'wav'

            filename = os.path.join(temp_dir, f'tts_part_{i}.{temp_format}')

            if len(chapters) > 1:
                log(LOG_TYPE.INFO, f'Synthesizing chapter {i + 1} of {len(chapters)}')

            if len(chapter.tts_items) > 0:
                for j, tts_item in enumerate(chapter.tts_items):
                    if tts_item.text:
                        speaker = tts_item.speaker or self.preferred_speakers[tts_item.speaker_idx]
                        log(LOG_TYPE.INFO, f'Synthesizing item {j + 1} of {len(chapter.tts_items)} ("{speaker}", {tts_item.speaker_idx}, {tts_item.length}ms):{bcolors.ENDC} {tts_item.text}')
                    else:
                        log(LOG_TYPE.INFO, f'Adding pause: {tts_item.length}ms:{bcolors.ENDC} {tts_item.text}')

                    audio += tts_processor.synthesize_tts_item(tts_item)

                    if callback is not None:
                        callback(100/(len(chapters) * len(chapter.tts_items)) * (i + j), tts_item)

                current_total_items += len(chapter.tts_items)

                self._write_temp_audio(audio, filename)

                num_zeros = len(str(len(self.temp_files)))
                chapter_title = f'{i + 1:0{num_zeros}} - {chapter.title}'

                filename_out = os.path.join(temp_dir, f'tts_part_{i}.{temp_format}')

                # Add temp files for concatenating later
                self.temp_files.append((chapter_title, filename_out))

            chapter.start_time = cumulative_time
            chapter.end_time = cumulative_time + self._get_nanoseconds_for_file(filename)
            cumulative_time = chapter.end_time

        del tts_processor

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
            audio = ffmpeg.input(input_file)['a']
            image_path = os.path.join(temp_dir, 'tts_image.jpeg')

            # Fix for ffmpeg problem when image size is not divisible by 2
            image.crop((0, 0, math.ceil(image_width/2)*2, math.ceil(image_height/2)*2)).save(image_path)

            cover = ffmpeg.input(image_path)['v']

            (
                ffmpeg
                .output(audio, cover, output_file, vcodec='copy', acodec='copy', map_metadata=0, **{'disposition:v:0': 'attached_pic'}, loglevel='error')
                .run(overwrite_output=True)
            )

    def _write_temp_audio(self, segment: AudioSegment, output_filename: str) -> None:
        """
        Convert and write chapter AudioSegment as temporary audio file for later concatenation

        :param segment: AudioSegment to be written
        :type segment: AudioSegment

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """

        comp_expansion = 12.5
        comp_raise = 0.0001

        # Apply dynamic compression
        params = ['-filter', f'speechnorm=e={comp_expansion}:r={comp_raise}:l=1']
        bitrate = '320k'
        format = 'wav'
        segment.export(output_filename, format, parameters=params, bitrate=bitrate)

    def synthesize_and_write(self, project_filename: str, temp_dir_prefix: str = '', concat=True, callback: Callable[[float, TTS_Item], None] | None = None) -> None:
        """
        Synthesize and write the output audio files for the given project.

        :param project_filename: The project name.
        :type project_filename: str

        :param temp_dir_prefix: An optional prefix for the temporary directory name used during synthesis.
        :type temp_dir_prefix: str

        :param concat: A boolean value indicating whether to concatenate the audio files into a single file or not. Defaults to True.
        :type concat: bool

        :param callback: An optional callback function that will be called periodically during synthesis with progress information.
        :type callback: Callable[[float, TTS_Item], None] | None

        :return: None

        :raises: ValueError if `project_filename` is not a valid file path.
        """

        if not self.project.tts_chapters:
            log(LOG_TYPE.ERROR, f'No chapters to synthesize, exiting')
            return

        with tempfile.TemporaryDirectory(prefix=temp_dir_prefix) as temp_dir:
            try:
                log(LOG_TYPE.INFO, f'Synthesizing {self.project.title}')

                if self.model and self.vocoder:
                    t = TTS_Processor(self.model, self.vocoder, self.preferred_speakers)
                else:
                    match self.project.lang_code:
                        case 'en':
                            self.model = 'tts_models/en/vctk/vits'
                            self.vocoder = ''
                        case 'de':
                            self.model = 'tts_models/de/thorsten/tacotron2-DDC'
                            self.vocoder = 'vocoder_models/de/thorsten/hifigan_v1'
                        case _:
                            raise ValueError(f'Language code {self.project.lang_code} not supported')

                    t = TTS_Processor(self.model, self.vocoder, self.preferred_speakers)

                self._synthesize_chapters(self.project.tts_chapters, temp_dir, t, callback)

            except Exception as e:
                log(LOG_TYPE.ERROR, f'Synthesizing {self.project.title} failed: {e}')
                sys.exit(1)

            finally:
                # Prepare chapter metadata
                metadata_lines = [';FFMETADATA1\n']

                for chapter in self.project.tts_chapters:
                    metadata_lines.append(f'[CHAPTER]\nSTART={chapter.start_time}\nEND={chapter.end_time}\ntitle={chapter.title}\n')

                metadata = ''.join(metadata_lines)
                metadata_filename = os.path.join(temp_dir, 'metadata')

                # Write all the custom metadata to the new metadata file
                with open(metadata_filename, 'w') as metadata_file:
                    metadata_file.write(metadata)

                output_filename = os.path.join(self.project_path, sanitize_filename(project_filename))
                output_extension = f'.{self.output_format}'

                # Shorten path if needed
                output_filename = output_filename[:255 - len(output_extension)]
                output_path = output_filename + output_extension

                output_files: list[str] = []

                # Create directory if needed
                os.makedirs(self.project_path, exist_ok=True)

                # Concatenate all files, adding metadata and cover image (if set)
                if concat:
                    infiles = [ffmpeg.input(file) for _, file in self.temp_files]

                    metadata_input = ffmpeg.input(metadata_filename)

                    if self.output_format not in ['m4b', 'm4a']:
                        log(LOG_TYPE.WARNING, f'Chapters are only possible for m4b/m4a at the moment.')

                    cmd = (
                        ffmpeg
                        .concat(*infiles, v=0, a=1)
                        .output(metadata_input, output_path, map_metadata=1, **{'metadata': f'title={self.project.title}', 'metadata:': f'album={self.project.subtitle}', 'metadata:g': f'artist={self.project.author}'}, loglevel='error')
                        .compile(overwrite_output=True)
                    )

                    # Remove last map parameter (workaround for ffmpeg-python bug)
                    cmd = self._remove_last_arg(cmd, '-map')

                    subprocess.call(cmd)

                    output_files.append(output_path)
                    log(LOG_TYPE.SUCCESS, f'Synthesizing project {self.project.title} finished, file saved as {output_path}')
                else:
                    # Don’t concatenate, convert the chapter temp files to the target format
                    os.makedirs(output_filename, exist_ok=True)

                    for name, file in self.temp_files:
                        output_chapter_filename = os.path.join(output_filename, name + output_extension)

                        output_args = {'metadata': f'title={self.project.title} - {name}', 'metadata:': f'album={self.project.subtitle}', 'metadata:g': f'artist={self.project.author}'}

                        if self.output_format == 'mp3':
                            output_args['audio_bitrate'] = '320k'

                        # Convert to target format, adding metadata
                        (
                            ffmpeg
                            .input(file)
                            .output(output_chapter_filename, **output_args, loglevel='error')
                            .run(overwrite_output=True)
                        )

                        output_files.append(output_chapter_filename)
                    log(LOG_TYPE.SUCCESS, f'Synthesizing project {self.project.title} finished, chapter files saved under {output_filename}/')

                if self.project.image_bytes:
                    if self.output_format in ['m4b', 'm4a', 'mp3']:
                        image_bytes = base64.b64decode(self.project.image_bytes)
                        image_file = io.BytesIO(image_bytes)
                        image = Image.open(image_file)

                        if image.format:
                            image_added = False
                            for output_file in output_files:
                                # Add image
                                output_path_with_image = output_file + '_tmp' + output_extension

                                self._add_image(image, output_file, output_path_with_image)
                                os.remove(output_file)
                                os.rename(output_path_with_image, output_file)
                                image_added = True

                            if image_added:
                                log(LOG_TYPE.SUCCESS, 'Project image added to final output for all files.')
                    else:
                        log(LOG_TYPE.WARNING, f'Images are only possible for m4b/m4a and mp3 at the moment.')
