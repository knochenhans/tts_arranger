from abc import ABC, abstractmethod
from tts_arranger.items.tts_project import TTS_Project
from loguru import logger
from tts_arranger.ssml_builder import SSMLBuilder


class ProjectConverter(ABC):
    def __init__(self, project: TTS_Project):
        self.project = project


class ProjectConverterSSML(ProjectConverter):
    def convert(self) -> str:
        builder = SSMLBuilder()
        builder.add_metadata(
            title=self.project.title,
            description=self.project.subtitle,
            date=self.project.date.strftime("%Y-%m-%d"),
            creators=[self.project.author],
            language=self.project.lang_code,
        )
        current_voice = None
        for chapter in self.project.chapters:
            for item in chapter.items:
                for element in item.elements:
                    if element.speaker_id:
                        if element.speaker_id != current_voice:
                            current_voice = element.speaker_id
                            builder.add_voice(name=current_voice)
                            builder.add_sentence(element.text)
                    else:
                        if element.min_length:
                            builder.add_break(time=str(element.min_length) + "ms")
        return builder.to_string()

    def save_to_file(self, filename: str) -> None:
        ssml_content = self.convert()
        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                file.write(ssml_content)
        except IOError as e:
            logger.error(f"Error writing to file {filename}: {e}")
            raise
