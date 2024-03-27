import os
from abc import ABC
from typing import Callable, Optional

from .. import TTS_Project  # type: ignore


class TTS_Abstract_Reader(ABC):
    """
    Abstract base class for converting files into a TTS project.
    """

    def __init__(self):
        """
        Initializes the reader with some default parameters
        """

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
