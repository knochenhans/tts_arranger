import datetime
import os
import sys
import time

from pydub import AudioSegment  # type: ignore

from .items.tts_item import TTS_Item
from .tts_processor import TTS_Processor
from .utils.log import LOG_TYPE, bcolors, log


class TTS_Simple_Writer():
    """
    Simple writer class that takes a list of TTS items (in contrast to a more complex TTS_Project object), synthesizes, and writes them as a final audio file
    """

    def __init__(self, tts_items: list[TTS_Item]):
        self.tts_items = tts_items

        self.final_segment: AudioSegment

    def synthesize_and_write(self, output_filename: str):
        """
        Synthesize and write list of items as an audio file

        :param tts_items: List of TTS items to be synthesized
        :type tts_items: list

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """
        time_total = 0.0
        time_needed = 0.0

        characters_sum = 0
        characters_total = 0

        tts_processor = TTS_Processor()
        tts_processor.initialize()

        tts_items = tts_processor.preprocess_items(self.tts_items)

        for tts_item in tts_items:
            characters_sum += len(tts_item.text)

        segments = AudioSegment.empty()

        for idx, tts_item in enumerate(tts_items):
            if tts_item.text:
                log(LOG_TYPE.INFO, f'Synthesizing item {idx + 1} of {len(tts_items)} "({tts_item.speaker}", {tts_item.speaker_idx}, {tts_item.length}ms):{bcolors.ENDC} {tts_item.text}')
            else:
                log(LOG_TYPE.INFO, f'Adding pause: {tts_item.length}ms:{bcolors.ENDC} {tts_item.text}')

            if time_needed:
                log(LOG_TYPE.INFO, f'(Remaining time: {str(datetime.timedelta(seconds=round(time_needed)))})')

            time_last = time.time()

            try:
                segments += tts_processor.synthesize_tts_item(tts_item)

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
                log(LOG_TYPE.ERROR, f'Error synthesizing "{output_filename}": {e}')
                sys.exit()

        self._write(segments, output_filename)
        log(LOG_TYPE.SUCCESS, f'Synthesizing finished, file saved under {output_filename}.')

    def _write(self, segment: AudioSegment, output_filename: str) -> None:
        """
        Compress, convert and write AudioSegment as a given output file path and name

        :param segment: AudioSegment to be written
        :type segment: AudioSegment

        :param output_filename: Absolute path and filename of output audio file including file type extension (for example mp3, ogg)
        :type output_filename: str

        :return: None
        :rtype: None
        """
        # Clean up to free up some memory
        # self.synthesizer = None
        # gc.collect()

        # Set default format to mp3
        format = os.path.splitext(output_filename)[1][1:] or 'mp3'

        folder = os.path.dirname(os.path.abspath(output_filename))

        os.makedirs(folder, exist_ok=True)

        # Ensure output file name has a file extension
        output_filename = os.path.splitext(output_filename)[0] + '.' + format

        log(LOG_TYPE.INFO, f'Compressing, converting and saving as {output_filename}')

        comp_expansion = 12.5
        comp_raise = 0.0001

        # Apply dynamic compression
        # segment.export(output_filename, format, parameters=['-filter', 'speechnorm=e=25:r=0.0001:l=1', '-filter', 'loudnorm=tp=-1.0:offset=7'])
        params = ['-filter', f'speechnorm=e={comp_expansion}:r={comp_raise}:l=1']
        bitrate = '320k' if format == 'mp3' else None
        segment.export(output_filename, format, parameters=params, bitrate=bitrate)
