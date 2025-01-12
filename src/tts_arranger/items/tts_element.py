from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class TTS_Element:
    text: str = ""
    speaker_id: str = ""
    min_length: int = 0
    custom_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json(cls: type["TTS_Element"], json_data: Dict[str, Any]) -> "TTS_Element":
        return cls(
            text=json_data.get("text", ""),
            speaker_id=json_data.get("speaker_id", ""),
            min_length=json_data.get("min_length", 0),
            custom_data=json_data.get("custom_data", None),
        )

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    def __post_init__(self) -> None:
        # Mark pauses by invalidating speaker index
        if self.text == "" and self.min_length > 0:
            self.speaker_id = ""

    def __str__(self) -> str:
        return self.text