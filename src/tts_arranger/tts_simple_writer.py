import datetime
import io
import os
import sys
import tempfile
import time
from typing import Callable, Optional

import ffmpeg  # type: ignore
import numpy as np
import scipy.io.wavfile  # type: ignore

from .items.tts_item import TTS_Item
from .tts_abstract_writer import TTS_Abstract_Writer
from .tts_processor import TTS_Processor
from .utils.log import LOG_TYPE, bcolors, log


class TTS_Simple_Writer(TTS_Abstract_Writer):
    """
    Simple writer class that takes a list of TTS items (in contrast to a more complex TTS_Project object), synthesizes, and writes them as a final audio file
    """

    def __init__(self, tts_items: list[TTS_Item], preferred_speakers: Optional[list[str]] = None):
        super().__init__(preferred_speakers)

        self.tts_items = tts_items

        self.final_numpy: np.ndarray

    def synthesize_and_write(self, output_filename: str, lang_code='en', callback: Optional[Callable[[float, TTS_Item], None]] = None, preprocess=True):
        """
        Synthesize and write list of items as an audio file

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """
        time_total = 0.0
        time_needed = 0.0

        characters_sum = 0
        characters_total = 0

        match lang_code:
            case 'en':
                self.model = 'tts_models/en/vctk/vits'
                self.vocoder = ''
            case 'de':
                self.model = 'tts_models/de/thorsten/tacotron2-DDC'
                self.vocoder = 'vocoder_models/de/thorsten/hifigan_v1'
            case _:
                raise ValueError(f'Language code "{lang_code}" not supported')

        tts_processor = TTS_Processor(self.model, self.vocoder, self.preferred_speakers)
        tts_processor.initialize()

        self.sample_rate = tts_processor.get_sample_rate()

        if preprocess:
            tts_items = tts_processor.preprocess_items(self.tts_items)
        else:
            tts_items = self.tts_items

        for tts_item in tts_items:
            characters_sum += len(tts_item.text)

        numpy_segments = np.array([0], dtype=np.float32)

        for idx, tts_item in enumerate(tts_items):
            self.print_progress(idx, len(tts_items), tts_item)

            if time_needed:
                log(LOG_TYPE.INFO, f'(Remaining time: {str(datetime.timedelta(seconds=round(time_needed)))}).')

            time_last = time.time()

            if callback is not None:
                callback(100/(len(tts_items) * idx), tts_item)

            try:
                numpy_segments = np.concatenate((numpy_segments, tts_processor.synthesize_tts_item(tts_item)))

                time_now = time.time()
                time_total += time_now - time_last
                characters_total += len(tts_item.text)

                if characters_total > 0:
                    time_needed = ((time_total / characters_total) * characters_sum) - time_total

                # Report progress
                # if callback is not None:
                #     callback(idx, len(tts_items))
            except KeyboardInterrupt:
                log(LOG_TYPE.ERROR, 'Stopped by user.')
                sys.exit()
            except Exception as e:
                # with open(self.temp_dir.name + '/tts-error.log', 'a+') as f:
                #     f.write(f'Error synthesizing "{output_filename}"\n')
                log(LOG_TYPE.ERROR, f'Error synthesizing "{output_filename}": {e}.')
                sys.exit()

        self._write(numpy_segments, output_filename, )
        log(LOG_TYPE.SUCCESS, f'Synthesizing finished, file saved as "{output_filename}".')

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
        # Clean up to free up some memory
        # self.synthesizer = None
        # gc.collect()

        # Set default format to mp3
        output_format = os.path.splitext(output_filename)[1][1:] or 'mp3'

        folder = os.path.dirname(os.path.abspath(output_filename))

        os.makedirs(folder, exist_ok=True)

        # Ensure output file name has a file extension
        output_filename = os.path.splitext(output_filename)[0] + '.' + output_format

        log(LOG_TYPE.INFO, f'Compressing, converting and saving as {output_filename}.')

        output_args = {}

        if output_format == 'mp3':
            output_args['audio_bitrate'] = '320k'

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, 'temp')
            scipy.io.wavfile.write(temp_path, self.sample_rate, numpy_segment)

            comp_expansion = 12.5
            comp_raise = 0.0001

            # Convert to target format
            (
                ffmpeg
                .input(temp_path)
                .filter('speechnorm', e=f'{comp_expansion}', r=f'{comp_raise}', l=1)
                .output(output_filename, **output_args, loglevel='error')
                .run(overwrite_output=True)
            )
