
from typing import Callable, Optional

from bs4 import BeautifulSoup, PageElement  # type: ignore

from tts_arranger.tts_reader.checker import Checker  # type: ignore

from .. import TTS_Project  # type: ignore
from .tts_html_based_reader import TTS_HTML_Based_Reader  # type: ignore


class TTS_HTML_Reader(TTS_HTML_Based_Reader):
    """
    Class for converting a HTML file into a TTS project.
    """

    def __init__(self, preferred_speakers: Optional[list[str]] = None, ignore_default_checkers=False, custom_checkers: Optional[list[Checker]] = None):
        super().__init__(preferred_speakers, custom_checkers, ignore_default_checkers=ignore_default_checkers)

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

    def load_raw(self, content: str, author: str = '', title: str = '', callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Load HTML content into the TTS_Project.

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
        super().load_raw(content, author, title, callback)

        soup = BeautifulSoup(content, 'html.parser')

        if isinstance(soup, PageElement):
            project = self.html_converter.convert_from_html(str(soup))

            # Get titles from first chapter items
            if isinstance(project, TTS_Project):
                project.get_titles()

            self.project.merge_from_project(project)

        self.project.author = self.author
        self.project.title = self.title
