from dataclasses import dataclass, field

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
