from typing import List, Optional

from tts_arranger.items.tts_element import TTS_Element


class ElementOptimizer:
    @staticmethod
    def merge_items(
        tts_elements: List[TTS_Element], join_char: str = ""
    ) -> List[TTS_Element]:
        final_elements: List[TTS_Element] = []
        merged_element: Optional[TTS_Element] = None

        for tts_element in tts_elements:
            if not merged_element:
                merged_element = tts_element
            elif (
                merged_element.speaker_id == tts_element.speaker_id
                and merged_element.custom_data == tts_element.custom_data
            ):
                merged_element = TTS_Element(
                    text=f"{merged_element.text}{join_char}{tts_element.text}",
                    speaker_id=merged_element.speaker_id,
                    min_length=merged_element.min_length + tts_element.min_length,
                    custom_data=merged_element.custom_data,
                )
            else:
                final_elements.append(merged_element)
                merged_element = tts_element

        if merged_element is not None:
            final_elements.append(merged_element)

        return final_elements

    @staticmethod
    def remove_empty_items(tts_items: List[TTS_Element]) -> List[TTS_Element]:
        return [
            element
            for element in tts_items
            if element.text.strip() or element.min_length > 0 or element.custom_data
        ]

    @staticmethod
    def optimize(
        elements: List[TTS_Element], max_pause_duration: int = 0, join_char: str = ""
    ) -> List[TTS_Element]:
        elements = ElementOptimizer.remove_empty_items(elements)
        merged_elements = ElementOptimizer.merge_items(elements, join_char)

        # Do not remove empty elements with min_length set
        non_empty_elements = [
            element
            for element in merged_elements
            if element.text.strip() or element.min_length > 0
        ]

        if max_pause_duration > 0:
            optimized_elements = []
            for element in non_empty_elements:
                if element.min_length > max_pause_duration:
                    element.min_length = max_pause_duration
                optimized_elements.append(element)
            return optimized_elements

        return non_empty_elements
