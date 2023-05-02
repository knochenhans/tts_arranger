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

    def get_project(self) -> TTS_Project:
        return self.project
