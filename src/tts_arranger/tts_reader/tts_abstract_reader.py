import os
from abc import ABC, abstractmethod
from typing import Callable, Optional

from tts_arranger.functions import load_default_config
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.tts_reader.text_splitter import TextSplitter


class TTS_Abstract_Reader(ABC):
    """
    Abstract base class for converting files into a TTS project.
    """

    def __init__(self, text_splitter: Optional[TextSplitter] = None) -> None:
        """
        Initializes the reader with some default parameters
        """

        self.project: TTS_Project = TTS_Project()
        self.title: str = ""
        self.author: str = ""

        config = load_default_config()
        self.text_splitter: TextSplitter = text_splitter or TextSplitter(
            config.get("gemini_api", "")
        )

    def _smart_truncate(
        self, content: str, length: int = 100, suffix: str = "…"
    ) -> str:
        """
        Shorten the given string without breaking words
        """
        if len(content) <= length:
            return content
        else:
            return " ".join(content[: length + 1].split(" ")[0:-1]) + suffix

    @abstractmethod
    def load(
        self, filename: str, callback: Optional[Callable[[float], None]] = None
    ) -> None:
        # Set filename as title
        self.title = os.path.splitext(os.path.basename(filename))[0]

    def load_raw(
        self,
        content: str,
        author: str = "",
        title: str = "",
        callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.author = author or self.author
        self.title = title or self.title

    def get_project(self) -> TTS_Project:
        return self.project
