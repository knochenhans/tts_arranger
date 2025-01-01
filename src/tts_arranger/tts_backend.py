from typing import Optional


class TTSBackend:
    def __init__(self, config: str):
        self.config = config

    def synthesize(self, text: str, config: Optional[dict] = None) -> bytes:
        return b""
    
    def cleanup(self):
        pass