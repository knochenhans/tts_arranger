from abc import ABC, abstractmethod
from typing import List, Optional
from tts_arranger.items.tts_project import TTS_Project
from tts_arranger.items.tts_element import TTS_Element
from loguru import logger
from tts_arranger.ssml_builder import SSMLBuilder


class ProjectConverter(ABC):
    def __init__(self, project: TTS_Project):
        self.project = project
        self.builder = None


class ProjectConverterSSML(ProjectConverter):
    def convert(self) -> str:
        self.builder = SSMLBuilder()
        self.builder.add_metadata(
            title=self.project.title,
            description=self.project.subtitle,
            date=self.project.date.strftime("%Y-%m-%d"),
            creators=[self.project.author],
            language=self.project.lang_code,
        )
        current_voice = None
        for chapter in self.project.chapters:
            for item in chapter.items:
                elements = self.concat_elements(item.elements)
                for element in elements:
                    # if element.custom_data:
                    #     tag = element.custom_data.get("tag")
                    #     if tag:
                    #         if "p" in tag:
                    #             self.builder.add_paragraph()
                    if element.speaker_id:
                        if element.speaker_id != current_voice:
                            current_voice = element.speaker_id
                            self.builder.add_voice(name=current_voice)
                        self.builder.add_sentence(element.text.strip())
                    else:
                        if element.min_length:
                            self.builder.add_break(time=str(element.min_length) + "ms")
        return self.builder.to_string()

    def concat_elements(self, elements: List) -> List[TTS_Element]:
        result: list = []
        current_element: Optional[TTS_Element] = None
        for element in elements:
            if current_element is None:
                current_element = element
            elif current_element.speaker_id == element.speaker_id:
                current_element.text += element.text
            elif element.custom_data:
                result.append(current_element)
                current_element = element
            else:
                result.append(current_element)
                current_element = element
        if current_element:
            result.append(current_element)
        return result

    def save_to_file(self, filename: str) -> None:
        ssml_content = self.convert()
        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                file.write(ssml_content)
        except IOError as e:
            logger.error(f"Error writing to file {filename}: {e}")
            raise
