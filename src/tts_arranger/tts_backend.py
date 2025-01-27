from typing import Dict, List, Optional

import numpy as np

TextItem = Dict[str, str | float]


class TTSBackend:
    def __init__(self, config: str):
        self.config = config

    def synthesize(self, text: str, config: Optional[dict] = None) -> bytes:
        return b""

    def synthesize_batch(self, text_items: List[TextItem]) -> List[np.ndarray]:
        return []

    def cleanup(self):
        pass

    def preprocess(self, text_items: List[TextItem]) -> List[TextItem]:
        return text_items