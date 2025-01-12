import base64
import datetime
import json
import pickle
from dataclasses import asdict, dataclass, field
from typing import List, Optional
from dateutil import parser

import requests  # type: ignore
from loguru import logger

from tts_arranger.items.tts_chapter import TTS_Chapter  # type: ignore
from tts_arranger.items.tts_item import TTS_Item  # type: ignore


@dataclass
class TTS_Project:
    tts_chapters: List[TTS_Chapter] = field(default_factory=list)

    title: str = ""
    subtitle: str = ""
    date: datetime.datetime = datetime.datetime.min
    author: str = ""
    lang_code: str = "en"
    image_bytes: bytes = bytes(0)

    raw: bool = False

    @classmethod
    def from_json_file(cls, filename: str = "") -> "TTS_Project":
        if filename:
            try:
                with open(filename, "r") as file:
                    json_data = file.read()
                    return cls.from_json(json_data)
            except IOError as e:
                logger.error(f"Error reading file {filename}: {e}")
                raise
        return TTS_Project()

    @classmethod
    def from_json(cls, json_data: str) -> "TTS_Project":
        try:
            data = json.loads(json_data)
            return cls(
                tts_chapters=[
                    TTS_Chapter.from_json(chapter)
                    for chapter in data.get("tts_chapters", [])
                ],
                title=data.get("title", ""),
                subtitle=data.get("subtitle", ""),
                date=parser.parse(data.get("date", datetime.datetime.min.isoformat())),
                author=data.get("author", ""),
                lang_code=data.get("lang_code", "en"),
                image_bytes=base64.b64decode(data.get("image_bytes", "")),
                raw=data.get("raw", False),
            )
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse JSON data: {e}")
            raise

    def to_json(self) -> str:
        try:
            data = asdict(self)
            data["date"] = self.date.isoformat()
            data["image_bytes"] = base64.b64encode(self.image_bytes).decode("utf-8")
            data["tts_chapters"] = [chapter.to_json() for chapter in self.tts_chapters]
            return json.dumps(data)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to convert to JSON: {e}")
            raise

    @classmethod
    def from_items(cls, tts_items: List[TTS_Item]) -> "TTS_Project":
        return TTS_Project([TTS_Chapter(tts_items)])

    def merge_from_project(self, project: "TTS_Project") -> None:
        if isinstance(project, TTS_Project):
            self.tts_chapters += project.tts_chapters

    def dump_as_json_file(self, filename: str) -> None:
        try:
            with open(filename, "wb") as file:
                pickle.dump(self, file)
        except IOError:
            logger.warning(
                f'TTS Project export file "{filename}" could not be opened for writing.'
            )

    def add_image_from_url(self, image_url: str) -> None:
        if image_url:
            # Identify as browser to avoid problems with servers like wikimedia
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
            }
            self.image_bytes = base64.b64encode(
                requests.get(image_url, headers=headers).content
            )

    # def _check_empty_chapter(self, chapter: TTS_Chapter) -> bool:
    #     for item in chapter.tts_items:
    #         if item.text.strip() != "":
    #             return False
    #     return True

    # def clean_empty_chapters(self) -> None:
    #     final_chapters: List[TTS_Chapter] = []

    #     # for chapter in self.tts_chapters:
    #     #     if len(chapter.tts_items) > 0:
    #     #         final_chapters.append(chapter)

    #     # Remove empty chapters
    #     for chapter in self.tts_chapters:
    #         final_items = []
    #         for item in chapter.tts_items:
    #             if item.text.strip() != "" or (
    #                 item.speaker_idx == -1 and item.length > 0
    #             ):
    #                 final_items.append(item)

    #         # Check if remaining items are all pauses
    #         if len(final_items) > 1:
    #             if not self._check_empty_chapter(TTS_Chapter(final_items)):
    #                 final_chapters.append(chapter)

    #     self.tts_chapters = final_chapters

    # def optimize(self, max_pause_duration: int = 0) -> None:
    #     for chapter in self.tts_chapters:
    #         chapter.optimize(max_pause_duration)

    def set_titles(self, only_empty: bool = True, max_length: int = 100) -> None:
        for chapter in self.tts_chapters:
            chapter.set_title(only_empty, max_length)

    def get_titles(self) -> None:
        pass

    def get_output_filename(self) -> str:
        return self.author + " - " + self.title

    def __str__(self) -> str:
        return " ".join([chapter.title for chapter in self.tts_chapters])

    def __len__(self) -> int:
        return len(self.tts_chapters)

    def __getitem__(self, key: int) -> TTS_Chapter:
        return self.tts_chapters[key]

    def __setitem__(self, key: int, value: TTS_Chapter) -> None:
        self.tts_chapters[key] = value

    def __delitem__(self, key: int) -> None:
        del self.tts_chapters[key]

    def insert(self, index: int, value: TTS_Chapter) -> None:
        self.tts_chapters.insert(index, value)

    def append(self, value: TTS_Chapter) -> None:
        self.tts_chapters.append(value)

    def extend(self, values: List[TTS_Chapter]) -> None:
        self.tts_chapters.extend(values)

    def remove(self, value: TTS_Chapter) -> None:
        self.tts_chapters.remove(value)

    def pop(self, index: int = -1) -> TTS_Chapter:
        return self.tts_chapters.pop(index)

    def clear(self) -> None:
        self.tts_chapters.clear()

    def copy(self) -> "TTS_Project":
        return TTS_Project(
            tts_chapters=self.tts_chapters.copy(),
            title=self.title,
            subtitle=self.subtitle,
            date=self.date,
            author=self.author,
            lang_code=self.lang_code,
            image_bytes=self.image_bytes,
            raw=self.raw,
        )
