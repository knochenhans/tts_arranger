import os
from abc import ABC
from typing import Callable, Optional

from .. import TTS_Item, TTS_Project, TTS_Writer  # type: ignore


class TTS_Abstract_Reader(ABC):
    def __init__(self, preferred_speakers: Optional[list[str]] = None):
        """
        :param preferred_speakers: Optional list of preferred speakers to use instead of the models predefined speaker list  
        :type preferred_speakers: Optional[list[str]]
        """

        self.preferred_speakers = preferred_speakers or []
        self.project = TTS_Project()

        self.title = ''
        self.author = ''

        self.output_format = 'm4b'

    def get_output_filename(self) -> str:
        """
        Get the output filename.

        :return: The output filename.
        :rtype: str
        """
        return self.project.author + ' - ' + self.project.title

    def _smart_truncate(self, content: str, length=100, suffix='…') -> str:
        """
        Shorten the given string without breaking words
        """
        if len(content) <= length:
            return content
        else:
            return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix

    def load(self, filename: str, callback: Optional[Callable[[float], None]] = None) -> None:
        # Set filename as title
        self.title = os.path.splitext(os.path.basename(filename))[0]

    def load_raw(self, content: str, author: str = '', title: str = '', callback: Optional[Callable[[float], None]] = None) -> None:
        self.author = author or self.author
        self.title = title or self.title

    def synthesize(self, output_filename: str, temp_dir_prefix='', callback: Optional[Callable[[float, TTS_Item], None]] = None) -> None:
        """
        Synthesize speech and write it to an audio file.

        :param filename: The name of the output audio file.
        :type filename: str

        :param temp_dir_prefix: Prefix for the temporary directory used during synthesis.
        :type temp_dir_prefix: str

        :param callback: A function that will be called repeatedly during synthesis to provide progress information and TTS items.
        :type callback: Optional[Callable[[float, TTS_Item], None]]

        :return: None
        """

        path, full_name = os.path.split(output_filename)
        filename, extension = os.path.splitext(full_name)

        writer = TTS_Writer(self.project, path, self.output_format, preferred_speakers=self.preferred_speakers)
        writer.synthesize_and_write(self.get_output_filename(), temp_dir_prefix, callback=callback, concat=False, optimize=True)

    def get_project(self) -> TTS_Project:
        return self.project
