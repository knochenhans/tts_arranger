from dataclasses import dataclass


@dataclass
class TTS_Item():
    """
    Represents a TTS item containing various information.

    :param text: The text to be synthesized. Can be left empty in combination with length > 0 to create a pause.
    :type text: str

    :param speaker_idx: The index of the speaker to be used if no speaker name is given. Wraps around based on the actual available speaker indexes per model.
    :type speaker_idx: int

    :param length: The minimum length in milliseconds. Will be padded if the actual synthesized text fragment is shorter, and ignored if it is longer.
    :type length: int
    """
    text: str = ''
    speaker_idx: int = 0
    length: int = 0

    @classmethod
    def from_json(cls, json_data: dict) -> 'TTS_Item':
        """
        Class method to load a TTS item from a JSON object.

        :param json_data: A dictionary representing the JSON object to be loaded.
        :type json_data: dict

        :return: A TTS item object loaded from the JSON object.
        :rtype: TTS_Item
        """
        return cls(
            text=json_data.get('text', ''),
            # speaker_idx=json_data.get('speaker_idx', 0),
            length=json_data.get('min_length', 0),
        )

    def __post_init__(self):
        # Mark pauses by invalidating speaker index
        if self.text == '' and self.length > 0:
            self.speaker_idx = -1
