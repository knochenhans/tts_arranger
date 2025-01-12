from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from tts_arranger.items.tts_element import TTS_Element


@dataclass
class TTS_Item:
    elements: List[TTS_Element] = field(default_factory=list)

    @classmethod
    def from_json(cls: type["TTS_Item"], json_data: Dict[str, Any]) -> "TTS_Item":
        elements = [
            TTS_Element.from_json(elem) for elem in json_data.get("elements", [])
        ]
        return cls(elements=elements)

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    def __post_init__(self) -> None:
        # Additional initialization if needed
        pass

    def __str__(self) -> str:
        return " ".join([elem.text for elem in self.elements])

    def __len__(self) -> int:
        return len(self.elements)

    def __getitem__(self, key: int) -> TTS_Element:
        return self.elements[key]

    def __setitem__(self, key: int, value: TTS_Element) -> None:
        self.elements[key] = value

    def __delitem__(self, key: int) -> None:
        del self.elements[key]

    def insert(self, index: int, value: TTS_Element) -> None:
        self.elements.insert(index, value)

    def append(self, value: TTS_Element) -> None:
        self.elements.append(value)

    def extend(self, values: List[TTS_Element]) -> None:
        self.elements.extend(values)

    def remove(self, value: TTS_Element) -> None:
        self.elements.remove(value)

    def pop(self, index: int = -1) -> TTS_Element:
        return self.elements.pop(index)

    def clear(self) -> None:
        self.elements.clear()

    def copy(self) -> "TTS_Item":
        return TTS_Item(elements=self.elements.copy())
