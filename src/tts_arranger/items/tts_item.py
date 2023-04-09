from dataclasses import dataclass


@dataclass
class TTS_Item():
    """
    Represents a TTS item containing various information.

    :param text: The text to be synthesized. Can be left empty in combination with length > 0 to create a pause.
    :type text: str

    :param speaker: The name of the speaker to be used.
    :type speaker: str

    :param speaker_idx: The index of the speaker to be used if no speaker name is given. Wraps around based on the actual available speaker indexes per model.
    :type speaker_idx: int

    :param length: The minimum length in milliseconds. Will be padded if the actual synthesized text fragment is shorter, and ignored if it is longer.
    :type length: int
    """
    text: str = ''
    speaker: str = ''
    speaker_idx: int = 0
    length: int = 0

    def __post_init__(self):
        # Mark pauses by invalidating speaker index
        if self.text == '' and self.length > 0:
            self.speaker_idx = -1
