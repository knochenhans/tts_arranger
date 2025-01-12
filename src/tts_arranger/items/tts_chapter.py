from dataclasses import asdict, dataclass, field
from typing import Optional, List, Dict, Any


from tts_arranger.items.tts_item import TTS_Item  # type: ignore
from tts_arranger.items.element_optimizer import ElementOptimizer  # type: ignore


@dataclass
class TTS_Chapter:
    items: List[TTS_Item] = field(default_factory=list)
    title: str = ""
    start_time: int = 0
    end_time: int = 0

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> "TTS_Chapter":
        tts_items = [TTS_Item.from_json(item) for item in json_data.get("items", [])]

        return cls(
            items=tts_items,
            title=json_data.get("title", ""),
        )

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    def optimize(self, max_pause_duration: int = 0) -> None:
        # self.tts_items = ItemOptimizer.optimize(self.tts_items, max_pause_duration)
        pass

    def set_title(self, only_empty: bool = True, max_length: int = 100) -> None:
        # if len(self.tts_items) > 0:
        #     self.title = (
        #         self.tts_items[0].text[:max_length] + "…"
        #         if len(self.tts_items[0].text) > max_length
        #         else self.tts_items[0].text
        #     )
        pass

    def __str__(self) -> str:
        return " ".join([str(item) for item in self.items])

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, key: int) -> TTS_Item:
        return self.items[key]

    def __setitem__(self, key: int, value: TTS_Item) -> None:
        self.items[key] = value

    def __delitem__(self, key: int) -> None:
        del self.items[key]

    def insert(self, index: int, value: TTS_Item) -> None:
        self.items.insert(index, value)

    def append(self, value: TTS_Item) -> None:
        self.items.append(value)

    def extend(self, values: List[TTS_Item]) -> None:
        self.items.extend(values)

    def remove(self, value: TTS_Item) -> None:
        self.items.remove(value)

    def pop(self, index: int = -1) -> TTS_Item:
        return self.items.pop(index)

    def clear(self) -> None:
        self.items.clear()

    def copy(self) -> "TTS_Chapter":
        return TTS_Chapter(
            items=self.items.copy(),
            title=self.title,
            start_time=self.start_time,
            end_time=self.end_time,
        )
