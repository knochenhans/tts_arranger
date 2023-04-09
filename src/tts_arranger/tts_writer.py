import base64
import io
import math
import os
import subprocess
import sys
import tempfile
from typing import Callable

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

    def __init__(self, project: TTS_Project = TTS_Project(),  base_path: str = '', output_format='m4b', model: str = '', vocoder: str = '') -> None:
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

    def _synthesize_chapters(self, chapters: list[TTS_Chapter], temp_dir: str, tts_arranger: TTS_Processor, callback: Callable[[float, TTS_Item], None] | None = None) -> None:
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
            chapter.tts_items = tts_arranger.preprocess_items(chapter.tts_items)

        tts_arranger.initialize()

        total_items = 0

        for chapter in chapters:
            total_items += len(chapter.tts_items)

        current_total_items = 0

        cumulative_time = 0

        for i, chapter in enumerate(chapters):
            # print(f'for {i}, {chapter.title} in enumerate(chapters):')
            audio = AudioSegment.empty()

            temp_format = 'mp4'

            if self.output_format != 'm4b':
                temp_format = 'wav'

            filename = temp_dir + '/' + f'tts_part_{i}.{temp_format}'

            log(LOG_TYPE.INFO, f'Synthesizing chapter {i + 1} of {len(chapters)}')

            for j, tts_item in enumerate(chapter.tts_items):
                # print(f'for {j}, tts_item in enumerate(chapter.tts_items):')
                if tts_item.text:
                    log(LOG_TYPE.INFO, f'Synthesizing item {j + 1} of {len(chapter.tts_items)} ("{tts_item.speaker}", {tts_item.speaker_idx}, {tts_item.length}ms):{bcolors.ENDC} {tts_item.text}')
                else:
                    log(LOG_TYPE.INFO, f'Adding pause: {tts_item.length}ms:{bcolors.ENDC} {tts_item.text}')

                audio += tts_arranger.synthesize_tts_item(tts_item)

                if callback is not None:
                    # callback(i + 1, len(chapters), j + 1, len(chapter.tts_items), chapter.title, current_total_items, total_items)
                    # callback((i * len(chapter.tts_items) + j + 1) / (len(chapters) * len(chapter.tts_items)) * 100)
                    # print(f'callback(100/({len(chapters)} * {len(chapter.tts_items)} * ({i} + {j}), tts_item)')
                    callback(100/(len(chapters) * len(chapter.tts_items)) * (i + j), tts_item)

            current_total_items += len(chapter.tts_items)

            tts_arranger.write(audio, filename)

            num_zeros = len(str(len(self.temp_files)))
            chapter_title = f'{i + 1:0{num_zeros}} - {chapter.title}'

            filename_out = temp_dir + '/' + f'tts_part_{i}.{temp_format}'

            # If the target format is not m4b, write individual files for chapters
            if self.output_format != 'm4b':
                title = self.project.title

                if self.project.subtitle:
                    title += ' - ' + self.project.subtitle

                # Convert to target format, adding metadata
                (
                    ffmpeg
                    .input(filename)
                    .output(filename_out, **{'metadata': f'title={chapter_title}', 'metadata:': f'album={title}', 'metadata:g': f'artist={self.project.author}'}, loglevel='error')
                    .run(overwrite_output=True)
                )

            # Add temp files for concatenating later
            self.temp_files.append((chapter_title, filename_out))

            chapter.start_time = cumulative_time
            chapter.end_time = cumulative_time + self._get_nanoseconds_for_file(filename)
            cumulative_time = chapter.end_time

        del tts_arranger

    def _remove_first_arg(self, cmd, arg: str):
        if cmd:
            index = cmd.index(arg)

            if index:
                cmd.pop(index)
                cmd.pop(index)

        return cmd

    def _remove_last_arg(self, cmd, arg: str):
        if cmd:
            cmd.reverse()

            index = cmd.index(arg)

            if index:
                cmd.pop(index - 1)
                cmd.pop(index - 1)

            cmd.reverse()
        return cmd

    def _add_image(self, image: Image.Image, input_file, output_file):
        image_width, image_height = image.size

        with tempfile.TemporaryDirectory() as temp_dir:
            audio = ffmpeg.input(input_file)['a']
            image_path = temp_dir + '/tts_image.jpeg'

            # Fix for ffmpeg problem when image size is not divisible by 2
            image.crop((0, 0, math.ceil(image_width/2)*2, math.ceil(image_height/2)*2)).save(image_path)

            cover = ffmpeg.input(image_path)['v']

            (
                ffmpeg
                .output(audio, cover, output_file, vcodec='copy', acodec='copy', map_metadata=0, **{'disposition:v:0': 'attached_pic'}, loglevel='error')
                .run(overwrite_output=True)
            )

    def synthesize_project(self, project_filename: str, temp_dir_prefix: str = '', callback: Callable[[float, TTS_Item], None] | None = None):
        if self.project.tts_chapters:
            with tempfile.TemporaryDirectory(prefix=temp_dir_prefix) as temp_dir:
                try:
                    log(LOG_TYPE.INFO, f'Synthesizing {self.project.title}')

                    if self.model and self.vocoder:
                        t = TTS_Processor(self.model, self.vocoder)
                    else:
                        match self.project.lang_code:
                            case 'en':
                                self.model = 'tts_models/en/vctk/vits'
                                self.vocoder = ''
                            case 'de':
                                self.model = 'tts_models/de/thorsten/tacotron2-DDC'
                                self.vocoder = 'vocoder_models/de/thorsten/hifigan_v1'

                        t = TTS_Processor(self.model, self.vocoder)

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
                    metadata_filename = f'{temp_dir}/metadata'

                    # Write all the custom metadata to the new metadata file
                    with open(metadata_filename, 'w') as metadata_file:
                        metadata_file.write(metadata)

                    output_filename = os.path.join(self.project_path, '') + str(sanitize_filename(project_filename))
                    output_extension = '.' + self.output_format

                    # Shorten path if needed
                    output_filename = output_filename[:255 - len(output_extension)]
                    output_path = output_filename + output_extension

                    # Create directory if needed
                    os.makedirs(self.project_path, exist_ok=True)

                    # Concatenate all files, adding metadata and cover image (if set)
                    if self.output_format == 'm4b':
                        infiles = []

                        for _, file in self.temp_files:
                            infiles.append(ffmpeg.input(file))

                        metadata_input = ffmpeg.input(f'{metadata_filename}')

                        cmd = (
                            ffmpeg
                            .concat(*infiles, v=0, a=1)
                            .output(metadata_input, output_path, map_metadata=1, **{'metadata': f'title={self.project.title}', 'metadata:': f'album={self.project.subtitle}', 'metadata:g': f'artist={self.project.author}'}, loglevel='error')
                            .compile(overwrite_output=True)
                        )

                        # Remove last map parameter (workaround for ffmpeg-python bug)
                        cmd = self._remove_last_arg(cmd, '-map')

                        subprocess.call(cmd)

                        # Add image
                        output_path_with_image = output_filename + '_tmp' + output_extension

                        if self.project.image_bytes:
                            image_bytes = base64.b64decode(self.project.image_bytes)
                            image_file = io.BytesIO(image_bytes)
                            image = Image.open(image_file)

                            if image.format:
                                log(LOG_TYPE.INFO, f'Adding first found image as cover')
                                self._add_image(image, output_path, output_path_with_image)
                                os.remove(output_path)
                                os.rename(output_path_with_image, output_path)

                    else:
                        # For all other formats, don’t concatenate, just reuse the tempfiles
                        os.makedirs(output_filename, exist_ok=True)

                        for name, file in self.temp_files:
                            destination = output_filename + '/' + f'{name}.{self.output_format}'
                            os.rename(file, destination)

            log(LOG_TYPE.INFO, f'Synthesizing {self.project.title} finished, file saved under {output_path}.')
        else:
            log(LOG_TYPE.ERROR, f'No chapters to synthesize, exiting')
