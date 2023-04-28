import datetime
import os
import re
from typing import Callable, Optional

import srt  # type: ignore

from .. import TTS_Item, TTS_Project, TTS_Simple_Writer  # type: ignore
from .tts_abstract_reader import TTS_Abstract_Reader  # type: ignore


class TTS_SRT_Reader(TTS_Abstract_Reader):
    def __init__(self, preferred_speakers: Optional[list[str]] = None):
        super().__init__(preferred_speakers)

        self.output_format = 'wav'

    def load(self, filename: str, callback: Optional[Callable[[float], None]] = None) -> None:
        super().load(filename, callback)
        with open(filename, 'r') as file:
            self.load_raw(file.read())

    def load_raw(self, content: str, author: str = '', title: str = '', callback: Optional[Callable[[float], None]] = None) -> None:
        srt_generator = srt.parse(content)
        subtitles = list(srt_generator)

        items: list[TTS_Item] = []

        # Start offset
        last_end: datetime.timedelta = datetime.timedelta()

        for line in subtitles:
            items.append(TTS_Item(length=int((line.start - last_end).total_seconds() * 1000)))

            # format the timedelta object
            formatted_td = str((line.start - last_end).total_seconds() * 1000).split(".")
            time_str = formatted_td[0]  # get the time string in the format HH:MM:SS
            milliseconds_str = formatted_td[1][:3]  # get the first 3 digits of the milliseconds string

            # concatenate the time string and milliseconds string
            formatted_time = f"{time_str},{milliseconds_str}"

            # print the formatted time string
            print('Pause: ' + formatted_time)

            # Remove tags and line breaks
            text = re.sub('<[^<]+?>', '', line.content)
            text = text.replace('\n', ' ')

            length = (line.end - line.start).total_seconds() * 1000
            items.append(TTS_Item(text, 0, int(length)))

            # format the timedelta object
            formatted_td = str(length).split(".")
            time_str = formatted_td[0]  # get the time string in the format HH:MM:SS
            milliseconds_str = formatted_td[1][:3]  # get the first 3 digits of the milliseconds string

            # concatenate the time string and milliseconds string
            formatted_time = f"{time_str},{milliseconds_str}"

            # print the formatted time string
            print('Text: ' + formatted_time)

            last_end = line.end

        self.project = TTS_Project.from_items(items)
        self.project.lang_code = 'de'
        self.project.raw = True

    def synthesize(self, output_filename: str, temp_dir_prefix='', callback: Optional[Callable[[float, TTS_Item], None]] = None) -> None:
        path, full_name = os.path.split(output_filename)
        filename, extension = os.path.splitext(full_name)

        writer = TTS_Simple_Writer(self.project.tts_chapters[0].tts_items, self.preferred_speakers)
        writer.synthesize_and_write(output_filename + '.wav', lang_code=self.project.lang_code, callback=callback)
