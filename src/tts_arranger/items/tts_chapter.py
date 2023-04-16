from dataclasses import dataclass, field
from typing import Optional

from pydub import AudioSegment  # type: ignore

from .tts_item import TTS_Item  # type: ignore


@dataclass
class TTS_Chapter():
    """
    A data class representing a TTS chapter.

    :param tts_items: A list of TTS items representing the text items to be synthesized into audio. Default value is an empty list.
    :type tts_items: list[TTS_Item]

    :param title: A string representing the chapter title. Default value is an empty string.
    :type title: str

    :param start_time: A float representing the start time of the chapter in nanoseconds. Default value is 0.
    :type start_time: float

    :param end_time: A float representing the end time of the chapter in nanoseconds. Default value is 0.
    :type end_time: float

    :param audio: An AudioSegment object representing the synthesized audio for the chapter. Default value is an empty AudioSegment object.
    :type audio: AudioSegment
    """
    tts_items: list[TTS_Item] = field(default_factory=list)

    title: str = ''
    start_time = 0
    end_time = 0
    audio = AudioSegment.empty()

    def optimize(self, max_pause_duration=0) -> None:
        """
        Merge similar items for smoother synthesizing and avoiding unwanted pauses

        :param max_pause_duration: Maximum duration auf merged pauses
        :type max_pause_duration: int

        :return: None
        """

        final_items: list[TTS_Item] = []
        merged_item: Optional[TTS_Item] = None

        for tts_item in self.tts_items:
            if not merged_item:
                # Scanning not started
                merged_item = tts_item
            elif merged_item.speaker == tts_item.speaker and merged_item.speaker_idx == tts_item.speaker_idx:
                # Starting item and current are similar, add to merge item text and length
                merged_item = merged_item.__class__(
                    text=f'{merged_item.text}{tts_item.text}',
                    speaker=merged_item.speaker,
                    speaker_idx=merged_item.speaker_idx,
                    length=merged_item.length + tts_item.length
                )
            else:
                # Starting item and current are not similar, add last and current item, set this item as new starting item
                final_items.append(merged_item)
                merged_item = tts_item

        if merged_item is not None:
            final_items.append(merged_item)

        # Limit pause duration for pause items, ignore if max_pause_duration == 0
        for final_item in final_items:
            if final_item.speaker_idx == -1 and max_pause_duration > 0:
                if final_item.length > max_pause_duration:
                    final_item.length = max_pause_duration

        self.tts_items = final_items
