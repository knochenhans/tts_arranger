from typing import Callable, Optional

from .. import TTS_Item, TTS_Project  # type: ignore
from .tts_abstract_reader import TTS_Abstract_Reader  # type: ignore


class TTS_Text_Reader(TTS_Abstract_Reader):
    """
    Class for converting a simple text file into a TTS project.
    """

    def __init__(self, preferred_speakers: Optional[list[str]] = None):
        super().__init__(preferred_speakers)

    def load(self, filename: str, callback: Optional[Callable[[float], None]] = None) -> None:
        super().load(filename, callback)
        with open(filename, 'rb') as file:
            self.load_raw(file.read().decode('unicode_escape'))

    def load_raw(self, content: str, author: str = '', title: str = '', callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Load an text file and convert.

        :param content: The text string.
        :type content: str

        :param author: The author of the HTML file (will be used as the author of the audiobook).
        :type author: str

        :param title: The title of the HTML file (will be used as the title of the audiobook).
        :type title: str

        :return: None
        """
        super().load_raw(content, author, title, callback)

        items: list[TTS_Item] = []

        # Interpret double line breaks as paragraphs
        paragraphs = content.split('\n\n')

        for paragraph in paragraphs:
            items.append(TTS_Item(paragraph))

        if len(items) > 0:
            self.project = TTS_Project.from_items(items)

            # Use beginning of first item of first chapter as chapter title
            if len(self.project.tts_chapters) > 0:
                if len(self.project.tts_chapters[0].tts_items) > 0:
                    self.project.tts_chapters[0].title = self._smart_truncate(self.project.tts_chapters[0].tts_items[0].text)

        self.project.author = self.author
        self.project.title = self.title
