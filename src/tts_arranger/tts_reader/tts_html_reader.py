
from typing import Callable, Optional

from .tts_html_based_reader import TTS_HTML_Based_Reader  # type: ignore


class TTS_HTML_Reader(TTS_HTML_Based_Reader):
    """
    Class for converting a HTML file into a TTS project.
    """

    def load(self, filename: str, callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Load an HTML file into the TTS_Project.

        :param content: The HTML string.
        :type content: str

        :param author: The author of the HTML file (will be used as the author of the audiobook).
        :type author: str

        :param title: The title of the HTML file (will be used as the title of the audiobook).
        :type title: str

        :param callback: An optional function that takes a float between 0 and 1 representing the progress of the loading process as its argument. This can be used to periodically check on the loading progress. Defaults to None if not provided.
        :type callback: Optional[Callable[[float], None]]

        :return: None
        """
        super().load(filename, callback)
        with open(filename, 'r') as file:
            self.load_raw(file.read())
